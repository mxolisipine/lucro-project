import os
from pathlib import Path
import dj_database_url
import logging
import uuid

# --- CORRELATION ID CONTEXT (THREAD/ASYNC SAFE) ---
from contextvars import ContextVar

correlation_id_var = ContextVar("correlation_id", default=None)

def set_correlation_id(value=None):
    if value is None:
        value = str(uuid.uuid4())
    correlation_id_var.set(value)
    return value

def get_correlation_id():
    return correlation_id_var.get()

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv('SECRET_KEY', 'unsafe-secret-for-dev')
DEBUG = os.getenv('DEBUG', '1') == '1'
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'transactions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'middleware.observability.ObservabilityMiddleware', 
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'project.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]

WSGI_APPLICATION = 'project.wsgi.application'

DATABASE_URL = os.getenv('DATABASE_URL', '')
if DATABASE_URL:
    DATABASES = {'default': dj_database_url.parse(DATABASE_URL)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'

# Celery
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ACKS_LATE = True


# --- FORMATTERS ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        # -----------------------------
        # HTTP REQUEST/RESPONSE FORMATTER
        # -----------------------------
        "http_json": {
            "format": (
                '{'
                '"timestamp":"%(asctime)s",'
                '"level":"%(levelname)s",'
                '"logger":"%(name)s",'
                '"message":"%(message)s",'
                '"correlation_id":"%(correlation_id)s",'
                '"method":"%(method)s",'
                '"path":"%(path)s",'
                '"type":"http",'
                '"client_ip":"%(client_ip)s",'
                '"user_agent":"%(user_agent)s",'
                '"status_code":"%(status_code)s",'
                '"response_bytes":"%(response_bytes)s",'
                '"duration_sec":"%(duration_sec)s"'
                '}'
            )
        },

        # -----------------------------
        # CELERY TASK FORMATTER
        # -----------------------------
        "celery_json": {
            "format": (
                '{'
                '"timestamp":"%(asctime)s",'
                '"level":"%(levelname)s",'
                '"logger":"%(name)s",'
                '"message":"%(message)s",'
                '"correlation_id":"%(correlation_id)s",'
                '"task_name":"%(task_name)s",'
                '"task_id":"%(task_id)s",'
                '"queue":"%(queue)s",'
                '"retries":"%(retries)s",'
                '"duration_sec":"%(duration_sec)s",'
                '"type":"celery"'
                '}'
            )
        },
    },

    "handlers": {
        # HTTP handler
        "http_handler": {
            "class": "logging.StreamHandler",
            "formatter": "http_json",
        },

        # Celery handler
        "celery_handler": {
            "class": "logging.StreamHandler",
            "formatter": "celery_json",
        },

        # Fallback debug logger
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "http_json",
        },
    },

    "loggers": {
        # -----------------------------
        # HTTP LOGGER
        # -----------------------------
        "observability.http": {
            "handlers": ["http_handler"],
            "level": "INFO",
            "propagate": False,
        },

        # -----------------------------
        # CELERY TASK LOGGER
        # -----------------------------
        "observability.tasks": {
            "handlers": ["celery_handler"],
            "level": "INFO",
            "propagate": False,
        },

        # Root fallback (optional)
        "": {
            "handlers": ["console"],
            "level": "WARNING",
        },
    },
}
