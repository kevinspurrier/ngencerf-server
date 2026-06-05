import os
import time
import base64
import jwt
import boto3
import requests
from django.conf import settings

# Global cache for the secret so we don't hit Secrets Manager on every API call
_SLURM_JWT_SECRET = None

def get_slurm_jwt_secret() -> str | bytes:
    """
    Fetches the Slurm JWT Secret (Munge Key) dynamically.
    If using AWS PCS, it fetches the secret via its ARN using boto3 and base64-decodes it.
    If not using AWS PCS, it falls back to the local SLURM_JWT_SECRET environment variable.
    """
    global _SLURM_JWT_SECRET
    if _SLURM_JWT_SECRET:
        return _SLURM_JWT_SECRET

    if getattr(settings, 'NGEN_ENVIRONMENT', '') == 'AWS_PCS':
        secret_arn = os.getenv("SLURM_JWT_SECRET_ARN")
        if not secret_arn:
            raise ValueError("SLURM_JWT_SECRET_ARN environment variable is missing!")

        # Fetch the secret dynamically using boto3
        session = boto3.Session()
        client = session.client('secretsmanager', region_name=session.region_name or 'us-east-1')
        response = client.get_secret_value(SecretId=secret_arn)
        
        # AWS PCS stores the Munge Key as a base64 string
        secret_string = response.get('SecretString')
        if not secret_string:
            raise ValueError("SecretString not found in SLURM_JWT_SECRET_ARN response")

        try:
            # The Munge key is base64 encoded by AWS PCS, so decode it to get the raw bytes
            # slurm/auth_jwt plugin uses the raw binary bytes of the key
            _SLURM_JWT_SECRET = base64.b64decode(secret_string)
        except Exception:
            # Fallback if it wasn't actually base64 encoded
            _SLURM_JWT_SECRET = secret_string
    else:
        # Fallback for local Docker testing
        _SLURM_JWT_SECRET = os.getenv("SLURM_JWT_SECRET")
        if not _SLURM_JWT_SECRET:
            raise ValueError("SLURM_JWT_SECRET is not configured in settings")

    return _SLURM_JWT_SECRET

def get_slurm_session() -> requests.Session:
    """
    Returns a standard requests Session object.
    AWS PCS Slurm REST API uses JWT, not SigV4.
    """
    return requests.Session()

def generate_slurm_jwt() -> str:
    """
    Generates a short-lived JSON Web Token (JWT) using the symmetric 
    HS256 secret configured for the AWS PCS Slurm REST API.
    """
    secret = get_slurm_jwt_secret()

    # The token is valid for 10 minutes
    expiration_time = int(time.time() + 600)

    # AWS PCS uses ec2-user (uid 1000) by default for Amazon Linux
    payload = {
        "exp": expiration_time,
        "iat": int(time.time()),
        "sun": getattr(settings, 'SLURM_REST_USER', 'ec2-user'),
        "uid": int(getattr(settings, 'SLURM_REST_UID', 1000)),
        "gid": int(getattr(settings, 'SLURM_REST_GID', 1000)),
        "gecos": "Slurm User",
        "dir": "/home/ec2-user",
        "shell": "/bin/bash",
        "id": {
            "gecos": "Slurm User",
            "dir": "/home/ec2-user",
            "gids": [int(getattr(settings, 'SLURM_REST_GID', 1000))],
            "shell": "/bin/bash"
        }
    }
    
    return jwt.encode(payload, secret, algorithm="HS256")
