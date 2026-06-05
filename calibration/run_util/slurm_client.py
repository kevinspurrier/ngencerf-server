import os
import base64
import boto3
import requests
from requests.auth import AuthBase
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
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

class Boto3SigV4Auth(AuthBase):
    """
    A custom authentication class for `requests` that signs HTTP requests
    using AWS Signature Version 4. This is required when communicating with
    the AWS PCS Slurm REST API endpoints.
    """
    def __init__(self):
        self.session = boto3.Session()
        self.credentials = self.session.get_credentials()
        self.region_name = self.session.region_name or 'us-east-1'
        self.service_name = 'execute-api' # AWS PCS VPC endpoints use API Gateway

    def __call__(self, r):
        # We must sign the exact request that `requests` is about to send
        request = AWSRequest(method=r.method, url=r.url, data=r.body, headers=dict(r.headers))
        SigV4Auth(self.credentials, self.service_name, self.region_name).add_auth(request)
        
        # Apply the generated signature headers back to the original request
        r.headers.update(dict(request.headers))
        return r

def get_slurm_session() -> requests.Session:
    """
    Returns a configured requests Session object for communicating with Slurm.
    If the environment is AWS PCS, it attaches the AWS SigV4 authentication handler.
    """
    session = requests.Session()
    
    if getattr(settings, 'NGEN_ENVIRONMENT', '') == 'AWS_PCS':
        session.auth = Boto3SigV4Auth()
        
    return session
