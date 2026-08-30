"""
Django settings - Production (Render)

Runtime invariants are strict for the live application. The single exception is
``collectstatic``: static asset compilation is a build-time operation and must
not require PostgreSQL, Redis, Cloudinary or SMTP to be reachable.
"""

import os
import re as _re

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from gestion_eebc.runtime_env import is_static_asset_build, normalize_runtime_environment
from .base import *
from .csp_policy import apply_csp4

apply_csp4(globals())
normalize_runtime_environment()
STATIC_ASSET_BUILD = is_static_asset_build()

# =============================================================================
# SECURITY
# =============================================================================
DEBUG = False

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('ALLOWED_HOSTS', '').split(',')
    if host.strip()
]

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip()
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
if not ALLOWED_HOSTS:
    if STATIC_ASSET_BUILD:
        ALLOWED_HOSTS = ['build.local']
    else:
        raise ImproperlyConfigured('ALLOWED_HOSTS must be configured in production.')

_env_secret = os.environ.get('SECRET_KEY', '').strip()
_secret_is_valid = (
    bool(_env_secret)
    and not _env_secret.startswith('django-insecure-')
    and len(_env_secret) >= 32
    and len(set(_env_secret)) >= 5
)
if not _secret_is_valid:
    if STATIC_ASSET_BUILD:
        _env_secret = 'eebc-static-build-secret-not-used-at-runtime-2026'
    else:
        raise ImproperlyConfigured(
            'SECRET_KEY must be a stable production secret with at least 32 characters.'
        )
SECRET_KEY = _env_secret

# Render terminates TLS at its edge.
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [
    r'^health/?$',
    r'^health/lite/?$',
    r'^health/ping/?$',
    r'^healthz/?$',
    r'^healthz/lite/?$',
    r'^healthz/ping/?$',
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

CSRF_TRUSTED_ORIGINS = [
    'https://gestion-eebc.onrender.com',
    'https://eglise-ebc.org',
    'https://www.eglise-ebc.org',
]

TRUSTED_CLIENT_IP_HEADER = os.environ.get('TRUSTED_CLIENT_IP_HEADER', '').strip()

# =============================================================================
# DATABASE
# =============================================================================
# collectstatic never needs application data. Using SQLite in-memory here keeps
# the build deterministic even when the production database is unavailable.
if STATIC_ASSET_BUILD:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
else:
    DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
    if DATABASE_URL:
        DATABASES = {
            'default': dj_database_url.config(
                default=DATABASE_URL,
                conn_max_age=600,
                conn_health_checks=True,
            )
        }
    else:
        required_db_env = ('DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST')
        missing_db_env = [name for name in required_db_env if not os.environ.get(name)]
        if missing_db_env:
            raise ImproperlyConfigured(
                'Configure DATABASE_URL or all explicit database variables. Missing: '
                + ', '.join(missing_db_env)
            )
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': os.environ['DB_NAME'],
                'USER': os.environ['DB_USER'],
                'PASSWORD': os.environ['DB_PASSWORD'],
                'HOST': os.environ['DB_HOST'],
                'PORT': os.environ.get('DB_PORT', '5432'),
                'CONN_MAX_AGE': 600,
                'CONN_HEALTH_CHECKS': True,
            }
        }

# =============================================================================
# CACHE / SESSIONS
# =============================================================================
REDIS_URL = os.environ.get('REDIS_URL', '').strip()
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'socket_connect_timeout': 5,
                'socket_timeout': 5,
            },
        }
    }
elif STATIC_ASSET_BUILD:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'eebc-static-build',
        }
    }
else:
    raise ImproperlyConfigured(
        'REDIS_URL is required in production. Security counters and rate limits '
        'must use a cache shared by every application worker.'
    )

if STATIC_ASSET_BUILD:
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
else:
    # cached_db keeps sessions durable in PostgreSQL while using Redis for speed.
    SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_CACHE_ALIAS = 'default'

# =============================================================================
# CELERY
# =============================================================================
if STATIC_ASSET_BUILD and not REDIS_URL:
    CELERY_BROKER_URL = 'memory://'
    CELERY_RESULT_BACKEND = 'cache+memory://'
else:
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL).strip()
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL).strip()

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Cayenne'
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# =============================================================================
# EMAIL - Hostinger
# =============================================================================
# The backend itself is selected in base.py via EMAIL_BACKEND.

# =============================================================================
# STRIPE
# =============================================================================
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY', '')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
STRIPE_SUCCESS_URL = os.environ.get('STRIPE_SUCCESS_URL', '')
STRIPE_CANCEL_URL = os.environ.get('STRIPE_CANCEL_URL', '')

# =============================================================================
# TWILIO
# =============================================================================
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER', '')

# =============================================================================
# META WHATSAPP CLOUD API
# =============================================================================
META_WHATSAPP_ACCESS_TOKEN = os.environ.get('META_WHATSAPP_ACCESS_TOKEN', '')
META_WHATSAPP_PHONE_NUMBER_ID = os.environ.get('META_WHATSAPP_PHONE_NUMBER_ID', '')
META_WHATSAPP_VERIFY_TOKEN = os.environ.get('META_WHATSAPP_VERIFY_TOKEN', '')
META_WHATSAPP_APP_SECRET = os.environ.get('META_WHATSAPP_APP_SECRET', '')
META_WHATSAPP_API_VERSION = os.environ.get('META_WHATSAPP_API_VERSION', 'v23.0')

# =============================================================================
# CAPTCHA
# =============================================================================
TURNSTILE_SITE_KEY = os.environ.get('TURNSTILE_SITE_KEY', '')
TURNSTILE_SECRET_KEY = os.environ.get('TURNSTILE_SECRET_KEY', '')
RECAPTCHA_PUBLIC_KEY = os.environ.get('RECAPTCHA_PUBLIC_KEY', '')
RECAPTCHA_PRIVATE_KEY = os.environ.get('RECAPTCHA_PRIVATE_KEY', '')
RECAPTCHA_REQUIRED_SCORE = float(os.environ.get('RECAPTCHA_REQUIRED_SCORE', 0.5))

# =============================================================================
# STATIC / MEDIA STORAGE
# =============================================================================
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL', '').strip()

if STATIC_ASSET_BUILD:
    # No user media is written while collecting static files.
    STORAGES['default'] = {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    }
else:
    if not CLOUDINARY_URL:
        raise ImproperlyConfigured(
            'CLOUDINARY_URL is required in production because Render local media '
            'storage is ephemeral.'
        )

    if 'cloudinary_storage' not in INSTALLED_APPS:
        INSTALLED_APPS.insert(
            INSTALLED_APPS.index('django.contrib.staticfiles'),
            'cloudinary_storage',
        )
    if 'cloudinary' not in INSTALLED_APPS:
        INSTALLED_APPS.append('cloudinary')

    STORAGES['default'] = {
        'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage',
    }

    _match = _re.match(r'cloudinary://([^:]+):([^@]+)@(.+)', CLOUDINARY_URL)
    if _match:
        CLOUDINARY_STORAGE = {
            'CLOUD_NAME': _match.group(3),
            'API_KEY': _match.group(1),
            'API_SECRET': _match.group(2),
        }
    else:
        CLOUDINARY_STORAGE = {
            'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
            'API_KEY': os.environ.get('CLOUDINARY_API_KEY', ''),
            'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', ''),
        }

if 'whitenoise.middleware.WhiteNoiseMiddleware' not in MIDDLEWARE:
    MIDDLEWARE.insert(2, 'whitenoise.middleware.WhiteNoiseMiddleware')

# =============================================================================
# SENTRY / LOGGING
# =============================================================================
SENTRY_DSN = os.environ.get('SENTRY_DSN', '').strip()
if SENTRY_DSN and not STATIC_ASSET_BUILD:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment='production',
    )

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
