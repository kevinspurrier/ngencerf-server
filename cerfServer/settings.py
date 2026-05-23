"""
Django settings for cerfServer project.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""
import codecs
import os
import re
from datetime import timedelta, datetime, timezone
from enum import StrEnum, auto

from datetimerange import DateTimeRange
from dotenv import load_dotenv

from calibration.enums_vanilla import NgenEnvironmentEnum, ScriptEnum, JobType

DJANGO_START_TIME = datetime.now(tz=timezone.utc)

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

FILE_PATH = os.path.abspath(str(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(FILE_PATH))
THIS_DIR = os.path.dirname(FILE_PATH)

dotenv_path = os.path.join(THIS_DIR, '.env')
print(f'Loading values from {dotenv_path}')
load_dotenv(dotenv_path)

version_path = os.path.join(BASE_DIR, 'version.env')
print(f'Loading values from {version_path}')
load_dotenv(version_path)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = str(os.getenv('DJANGO_DEBUG', 'true')).lower() == 'true'

NGENCERF_VERSION = os.getenv("NGENCERF_VERSION", "<unknown>")
NGENCERF_DATE = os.getenv("NGENCERF_DATE", "<unknown>")
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "<unknown>")
NGENCERF_COPYRIGHT = f"© 2024-{datetime.now().year}, RTX"

# used to find ngencerf-ui Docker image
NGENCERF_UI_TAG = os.getenv("NGENCERF_UI_TAG", "latest")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("CERF_SERVER_SECRET_KEY", "not-so-secret-key")

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django_dbconn_retry',
    'django.contrib.staticfiles',
    'drf_spectacular',
    'calibration.apps.CalibrationConfig',
    "rest_framework",
    "rest_framework.authtoken",
    "djoser",
    "rest_framework_simplejwt",
    'corsheaders',
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
]

# Points to which token model should be used for authentication. In case if only stateless
# tokens (e.g. JWT) are used in project it should be set to None.
TOKEN_MODEL = None

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'NgenCerf',
    'DESCRIPTION': 'Backend server for ngenCerf',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'calibration.util.middleware.TimingMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    "django_otp.middleware.OTPMiddleware",
    'calibration.util.middleware.ApiRequestDiagnosticsMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_currentuser.middleware.ThreadLocalUserMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'corsheaders.middleware.CorsMiddleware',
]

# Comma separated list in the env
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        'ALLOWED_HOSTS',
        '.localhost,127.0.0.1'
    ).split(',')
    if host.strip()
]

# Comma separated list in the env
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:3001",
    ).split(",")
    if origin.strip()
]

MFA_ENABLED = str(os.getenv("MFA_ENABLED", "false")).lower() == "true"

ACTIVE_DIRECTORY_ENABLED = str(os.getenv("ACTIVE_DIRECTORY_ENABLED", "false")).lower() == "true"

# Active Directory / LDAP
LDAP_DOMAIN = os.getenv("LDAP_DOMAIN", "nextgenwaterprediction.com").strip()

# Use the AD DNS name, not a specific DC IP, so failover can work.
LDAP_SERVER_URI = os.getenv("LDAP_SERVER_URI", f"ldap://{LDAP_DOMAIN}").strip()

# Base DN derived from nextgenwaterprediction.com
LDAP_USER_SEARCH_BASE_DN = os.getenv(
    "LDAP_USER_SEARCH_BASE_DN",
    "DC=nextgenwaterprediction,DC=com"
).strip()

LDAP_BIND_DN = os.getenv("LDAP_BIND_DN", "").strip()
LDAP_BIND_PASSWORD = os.getenv("LDAP_BIND_PASSWORD", "")

# sssd is using AD auth without SSL shown here, so default to ldap:// / non-SSL.
# Set LDAP_USE_SSL=true and LDAP_SERVER_URI=ldaps://... if LDAPS is configured later.
LDAP_USE_SSL = str(os.getenv("LDAP_USE_SSL", "false")).lower() == "true"

LDAP_TIMEOUT = int(os.getenv("LDAP_TIMEOUT", "10"))

LDAP_SYSTEM_NAME = os.getenv("LDAP_SYSTEM_NAME", "local").strip().lower()
LDAP_REQUIRED_GROUP_USERS = f"ngencerf-{LDAP_SYSTEM_NAME}-users"
LDAP_ADMIN_GROUP = f"ngencerf-{LDAP_SYSTEM_NAME}-admins"

ROOT_URLCONF = 'cerfServer.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = [
    "calibration.auth.active_directory_backend.ActiveDirectoryBackend",
    "calibration.auth.active_directory_backend.LocalUserBackup",
]

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv('REDIS_URL', "redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient"
        }
    }
}

AUTH_USER_MODEL = 'calibration.CustomUser'

DJOSER = {
    "SEND_CONFIRMATION_EMAIL": False,
    "SEND_ACTIVATION_EMAIL": False,
    "SET_PASSWORD_RETYPE": True,
    "UPDATE_LAST_LOGIN": True,
    "PASSWORD_RESET_CONFIRM_URL": "reset-password-confirm/{uid}/{token}",
    "SERIALIZERS": {
        "user_create": "calibration.user_serializers.CustomUserCreateSerializer",
        "user": "calibration.user_serializers.CustomUserSerializer",
        "current_user": "calibration.user_serializers.CustomUserSerializer",
    },
}

# https://django-rest-framework-simplejwt.readthedocs.io/en/latest/settings.html#settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'UPDATE_LAST_LOGIN': True,
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_OBTAIN_SERIALIZER': 'calibration.user_serializers.CustomTokenObtainPairSerializer',
}

WSGI_APPLICATION = 'cerfServer.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -----------------------------
# Enterprise Data
# -----------------------------
HYDROFABRIC_SOURCE = 'nhf'
ENTERPRISE_DATA_MODULE_METADATA_ENDPOINT = 'api/v1/modules/parameter_metadata/'
ENTERPRISE_DATA_OBSERVATION_DATA_INFO_ENDPOINT = 'api/v1/streamflow_observations/{gage_id}/info'
ENTERPRISE_DATA_OBSERVATION_DATA_ENDPOINT = 'api/v1/streamflow_observations/{gage_id}/csv'

ENTERPRISE_DATA_URL = os.getenv('ENTERPRISE_DATA_URL')
ENTERPRISE_DATA_ENV = os.getenv('ENTERPRISE_DATA_ENV')

# Default time range for BMI forcing data
FORCING_AORC_BMI_DATE_RANGE = DateTimeRange("1980-01-01T00:00:00+0000", "2024-12-31T23:59:59+0000")
FORCING_NWM_RETROSPECTIVE_BMI_DATE_RANGE = DateTimeRange("1980-01-01T00:00:00+0000", "2023-01-31T23:59:59+0000")

# Location of archive files
NGENCERF_ARCHIVE_S3_PATH = os.getenv('NGENCERF_ARCHIVE_S3_PATH')

# Location of download zip files on S3
NGENCERF_ZIPS_S3_PATH = os.getenv('NGENCERF_ZIPS_S3_PATH')
# AWS Profile to use for r/w buckets (.e.g, for archives and zips)
# Use None for AWS Dev (uses default profile)
NGENCERF_RW_PROFILE = os.getenv('NGENCERF_RW_PROFILE') or None

# Local temp directory for building ZIPs before upload (and for CLI zips)
ZIP_TEMP_DIR = os.path.join('/tmp', 'ngencerf-zips')
os.makedirs(ZIP_TEMP_DIR, exist_ok=True)

# How long a presigned download URL is valid
ZIP_DOWNLOAD_URL_TTL_SECONDS = 300

# How long the ZIP object is kept in S3 (and how long status is cached) before cleanup may delete it
ZIP_RETENTION_SECONDS = 3600

# -----------------------------
# ngen/nwm-cal-mgr Locations
# -----------------------------

# Locations for running nwm-cal-mgr

# Must match the repo root used in the docker container.
# It is not necessary for you to have local copies of the ngen and nwm-cal-mgr repos if you are using Docker
# But these directories still need to be set to reflect the directory of the repos in the docker container.
REPO_ROOT = '/ngen-app'
# Directory that Ngen is cloned into
NGEN_REPO_ROOT = os.path.join(REPO_ROOT, 'ngen')
# directory that nwm-cal-mgr is cloned into
CAL_MGR_REPO_ROOT = os.path.join(REPO_ROOT, 'nwm-cal-mgr')
NGEN_FORECAST_REPO_ROOT = os.path.join(REPO_ROOT, 'nwm-fcst-mgr')
NGEN_FORCING_REPO_ROOT = os.path.join(REPO_ROOT, 'ngen-forcing')
NWM_VERF_REPO_ROOT = os.path.join(REPO_ROOT, 'nwm-verf')

# This must match the data location in the ngen/nwm-cal-mgr docker
# Do not change this location.  You can put your data wherever you want, but you should then create a symbolic link to /ngencerf/data
# sudo mkdir /ngencerf
# sudo ln -s ~/your/data/dir /ngencerf/data
NGEN_CAL_MOUNT_POINT = '/ngencerf/data'
NGEN_CAL_DATA_PATH = os.getenv('NGEN_CAL_DATA_PATH', NGEN_CAL_MOUNT_POINT)

# Used only by get_git_info when running on PW
SINGULARITY_DIR = '/ngencerf/containers'

NGEN_LOGGING_DIR = os.path.join(BASE_DIR, 'logs')
print(f"Logging files will be created in {NGEN_LOGGING_DIR}")
os.makedirs(NGEN_LOGGING_DIR, exist_ok=True)

NGEN_STATIC_DIR = os.path.join(NGEN_CAL_MOUNT_POINT, 'ngen-static-files')
NGEN_CAL_WORK_DIR = os.path.join(NGEN_CAL_MOUNT_POINT, 'ngen-cal-work')
NGEN_VERIFICATION_WORK_DIR = os.path.join(NGEN_CAL_MOUNT_POINT, 'verification_work')
# The NGEN_BMI_FORCING_WORK_DIR directory is owned by ngen-forcing.  It will be responsible for creating it
NGEN_BMI_FORCING_WORK_DIR = os.path.join(NGEN_CAL_MOUNT_POINT, 'bmi_forcing_work')

# -----------------------------
# Forcing environments
# -----------------------------
FORCING_MESH_ENV = 'ngen_esmf_mesh_domain'
FORCING_EXTRACT_ENV = 'ngen_forcing_extraction'
FORCING_ENGINE_ENV = 'ngen_forcings_engine_bmi'

# Directory where all the output runs are stored
NGEN_CAL_RUN_DIR = os.path.join(NGEN_CAL_WORK_DIR, 'run_calib')

# Directory where verification runs are stored
NWM_VERF_RUN_DIR = os.path.join(NGEN_CAL_WORK_DIR, 'run_verif')

# Directory containing the nwm-cal-mgr virtual environment
# This is used only if we are running with NGEN_ENVIRONMENT=LOCAL and not in a separate container
NGEN_CAL_VENV = os.path.join(NGEN_CAL_WORK_DIR, 'venv.cal')

# Used when running in NGEN_ENVIRONMENT=DOCKER
# --rm ensures containers are auto-removed after exit
# Use {name} placeholder for the container name, which will be substituted at runtime
CAL_MGR_DOCKER_CMD = f'docker run --rm --network host --name {{name}} -v {NGEN_CAL_MOUNT_POINT}:{NGEN_CAL_MOUNT_POINT} nwm-cal-mgr'
NGEN_FORECAST_DOCKER_CMD = f'docker run --rm --name {{name}} -v {NGEN_CAL_MOUNT_POINT}:{NGEN_CAL_MOUNT_POINT} nwm-fcst-mgr'
NWM_VERF_DOCKER_CMD = f'docker run --rm --name {{name}} -v {NGEN_CAL_MOUNT_POINT}:{NGEN_CAL_MOUNT_POINT} nwm-verf'

# Used when running in NGEN_ENVIRONMENT=LOCAL
CAL_MGR_SCRIPT = os.path.join(CAL_MGR_REPO_ROOT, 'docker', 'run-nwm-cal-mgr.sh')
NGEN_FORECAST_SCRIPT = os.path.join(NGEN_FORECAST_REPO_ROOT, 'docker', 'run-ngen-fcst.sh')
NGEN_COLD_START_SCRIPT = os.path.join(NGEN_FORECAST_REPO_ROOT, 'docker', 'run-ngen-fcst.sh')
VERIFICATION_SCRIPT = os.path.join(NWM_VERF_REPO_ROOT, 'docker', 'run-nwm-verf.sh')

RUNTIME_INFO = {
    ScriptEnum.CALIBRATION: (CAL_MGR_DOCKER_CMD, CAL_MGR_SCRIPT),
    ScriptEnum.VALIDATION: (CAL_MGR_DOCKER_CMD, CAL_MGR_SCRIPT),
    ScriptEnum.VALIDATION_ITERATION: (CAL_MGR_DOCKER_CMD, CAL_MGR_SCRIPT),
    ScriptEnum.COLD_START: (NGEN_FORECAST_DOCKER_CMD, NGEN_COLD_START_SCRIPT),
    ScriptEnum.FORECAST: (NGEN_FORECAST_DOCKER_CMD, NGEN_FORECAST_SCRIPT),
    ScriptEnum.HINDCAST: (NGEN_FORECAST_DOCKER_CMD, NGEN_FORECAST_SCRIPT),
    ScriptEnum.VERIFICATION: (NWM_VERF_DOCKER_CMD, VERIFICATION_SCRIPT)
}

# -----------------------------
# Job Simulation Flags for use with NGEN_ENVIRONMENT=LOCAL or DOCKER
# -----------------------------
SIMULATE_FLAGS = {
    JobType.CALIBRATION: False,
    JobType.VALIDATION: False,
    JobType.FORECAST: False,
    JobType.VERIFICATION: False,
}

NGEN_ENVIRONMENT_STR = os.getenv('NGEN_ENVIRONMENT', NgenEnvironmentEnum.LOCAL.name)
try:
    # noinspection PyTypeHints
    NGEN_ENVIRONMENT = NgenEnvironmentEnum[NGEN_ENVIRONMENT_STR]
except KeyError:
    # noinspection PyUnresolvedReferences
    raise SystemExit(
        f"Invalid environment value for NGEN_ENVIRONMENT: {NGEN_ENVIRONMENT_STR}.  Must be one of {', '.join([e.name for e in NgenEnvironmentEnum])}")

# -----------------------------
# Slurm
# -----------------------------

SLURM_URL = os.getenv("SLURM_URL")
SLURM_JWT_SECRET = os.getenv("SLURM_JWT_SECRET")
# Native Slurm REST API Endpoints (v0.0.43 for Slurm 25.05+)
SLURM_OPENAPI_SUBMIT_ENDPOINT = 'slurm/v0.0.43/job/submit'

# Legacy Wrapper API Endpoints
SLURM_SUBMIT_CALIBRATION_JOB_ENDPOINT = 'submit-calibration-job'
SLURM_SUBMIT_VALIDATION_JOB_ENDPOINT = 'submit-validation-job'
SLURM_SUBMIT_COLD_START_JOB_ENDPOINT = 'submit-cold-start-job'
SLURM_SUBMIT_FORECAST_JOB_ENDPOINT = 'submit-forecast-job'
SLURM_SUBMIT_HINDCAST_JOB_ENDPOINT = 'submit-hindcast-job'
SLURM_SUBMIT_VERIFICATION_JOB_ENDPOINT = 'submit-verification-job'
SLURM_JOB_STATUS_ENDPOINT = 'job-status'
SLURM_CANCEL_JOB_ENDPOINT = 'cancel-job'

# -----------------------------
# Logging
# -----------------------------
VALID_LOG_LEVELS = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}


def get_log_level(env_var_name: str, default: str) -> str:
    value = os.getenv(env_var_name, default).upper().strip()

    if value not in VALID_LOG_LEVELS:
        raise SystemExit(
            f"Invalid log level for {env_var_name}: {value}. "
            f"Must be one of {', '.join(sorted(VALID_LOG_LEVELS))}"
        )

    return value


ROOT_LOG_LEVEL = get_log_level('NGENCERF_ROOT_LOG_LEVEL', 'INFO')
DEFAULT_LOG_LEVEL = get_log_level('NGENCERF_LOG_LEVEL', 'DEBUG')
DJANGO_LOG_LEVEL = get_log_level('NGENCERF_DJANGO_LOG_LEVEL', 'INFO')
DJANGO_REQUEST_LOG_LEVEL = get_log_level('NGENCERF_DJANGO_REQUEST_LOG_LEVEL', DJANGO_LOG_LEVEL)
DATABASE_LOG_LEVEL = get_log_level('NGENCERF_DATABASE_LOG_LEVEL', 'WARNING')
NGENCERF__LOG_LEVEL = get_log_level('NGENCERF_CALIBRATION_LOG_LEVEL', DEFAULT_LOG_LEVEL)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    # Root Logger: Sends everything to the console and file
    'root': {
        'handlers': ['console', 'file_dev'],
        'level': ROOT_LOG_LEVEL
    },

    'formatters': {
        'dev_format': {
            'format': '{asctime}.{msecs:03.0f} {module:15s} {levelname:8s} {funcName} {message}',
            'datefmt': '%Y-%m-%dT%H:%M:%S',
            'style': '{',
        },
        'simple': {
            'format': '{asctime}.{msecs:03.0f} {module:15s} {levelname:8s} {funcName} {message}',
            'datefmt': '%Y-%m-%dT%H:%M:%S',
            'style': '{',
        },
    },

    'handlers': {
        'console': {
            'level': DEFAULT_LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file_dev': {
            'level': DEFAULT_LOG_LEVEL,
            'class': 'logging.FileHandler',
            'filename': os.path.join(NGEN_LOGGING_DIR, 'ngencerf.log'),
            'formatter': 'dev_format',
            'encoding': 'utf-8',
        },
        'file_db': {
            'level': DATABASE_LOG_LEVEL,
            'class': 'logging.FileHandler',
            'filename': os.path.join(NGEN_LOGGING_DIR, 'ngencerf_db.log'),
            'formatter': 'dev_format',
            'encoding': 'utf-8',
        },
    },

    'loggers': {
        'django.db.backends': {
            'handlers': ['file_db'],
            'level': DATABASE_LOG_LEVEL,
            'propagate': False  # Prevents these logs from reaching the root logger (avoids duplication)
        },
        'django': {
            'handlers': ['console', 'file_dev'],
            'level': DJANGO_LOG_LEVEL,
            'propagate': False,  # Prevents these logs from reaching the root logger (avoids duplication)
        },
        'djoser': {
            'handlers': ['console', 'file_dev'],
            'level': DJANGO_LOG_LEVEL,
            'propagate': False,  # Prevents these logs from reaching the root logger (avoids duplication)
        },
        'rest_framework_simplejwt': {
            'handlers': ['console', 'file_dev'],
            'level': DJANGO_LOG_LEVEL,
            'propagate': False,  # Prevents these logs from reaching the root logger (avoids duplication)
        },
        'django.request': {
            'handlers': ['console', 'file_dev'],
            'level': DJANGO_REQUEST_LOG_LEVEL,
            'propagate': False,  # Prevents these logs from reaching the root logger (avoids duplication)
        },
        'django_dbconn_retry': {
            'handlers': ['console', 'file_dev'],
            'level': DJANGO_LOG_LEVEL,
            'propagate': False,
        },
        # Add these loggers for 'requests' and 'urllib3'
        'requests': {
            'handlers': ['console', 'file_dev'],
            'level': 'INFO',
            'propagate': False,  # Prevents these logs from reaching the root logger (avoids duplication)
        },
        'urllib3': {
            'handlers': ['console', 'file_dev'],
            'level': 'INFO',
            'propagate': False,  # Prevents these logs from reaching the root logger (avoids duplication)
        },
        'calibration': {
            'handlers': ['console', 'file_dev'],
            'level': NGENCERF__LOG_LEVEL,
            'propagate': False,  # Prevents these logs from reaching the root logger (avoids duplication)
        },
        'cerfServer': {
            'handlers': ['console', 'file_dev'],
            'level': NGENCERF__LOG_LEVEL,
            'propagate': False,  # Prevents these logs from reaching the root logger (avoids duplication)
        }
    }
}

# -----------------------------
# Database
# -----------------------------

DATABASE_OPTIONS = {
    'connect_timeout': int(os.getenv('CERF_SERVER_DATABASE_CONNECT_TIMEOUT', '10')),
    'options': os.getenv(
        'CERF_SERVER_DATABASE_OPTIONS',
        '-c statement_timeout=10000ms'
    ),
    'sslmode': os.getenv('CERF_SERVER_DATABASE_SSLMODE', 'require'),
}

sslrootcert = os.getenv('CERF_SERVER_DATABASE_SSLROOTCERT')

if sslrootcert:
    DATABASE_OPTIONS['sslrootcert'] = sslrootcert


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('CERF_SERVER_DATABASE_NAME', 'postgres'),
        'USER': os.getenv('CERF_SERVER_DATABASE_USER', 'postgres'),
        'PASSWORD': os.getenv('CERF_SERVER_DATABASE_PASSWORD', 'postgres'),
        'HOST': os.getenv('CERF_SERVER_DATABASE_HOST', 'localhost'),
        'PORT': int(os.getenv('CERF_SERVER_DATABASE_PORT', '5432')),
        'CONN_MAX_AGE': int(os.getenv('CERF_SERVER_DATABASE_CONN_MAX_AGE', '60')),
        'OPTIONS': DATABASE_OPTIONS,
    }
}
