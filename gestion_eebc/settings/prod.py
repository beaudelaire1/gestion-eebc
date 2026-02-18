"""
Django settings - Production (Render)
"""

import os
import dj_database_url
from .base import *

# =============================================================================
# SECURITY
# =============================================================================
DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Render specific
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# CSRF Trusted Origins (requis pour Django 4+)
CSRF_TRUSTED_ORIGINS = [
    'https://gestion-eebc.onrender.com',
    'https://eglise-ebc.org',
    'https://www.eglise-ebc.org',
]

# HTTPS
# SECURE_SSL_REDIRECT = False : Render gère le SSL à son edge proxy.
# Un redirect ici bloque les health checks HTTP internes de Render.
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS
SECURE_HSTS_SECONDS = 31536000  # 1 an
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Autres
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'


# =============================================================================
# DATABASE - PostgreSQL via DATABASE_URL (Render)
# =============================================================================
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'eebc'),
            'USER': os.environ.get('DB_USER', 'eebc'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': 60,
        }
    }


# =============================================================================
# CACHE - En mémoire pour le plan gratuit (pas de Redis)
# =============================================================================
REDIS_URL = os.environ.get('REDIS_URL')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }
    # Sessions en cache Redis
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    # Cache en mémoire locale (plan gratuit)
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }
    # Sessions en base de données
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'


# =============================================================================
# CELERY (optionnel - si Redis disponible)
# =============================================================================
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', os.environ.get('REDIS_URL'))
if CELERY_BROKER_URL:
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', CELERY_BROKER_URL)
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_TIMEZONE = 'America/Cayenne'
    CELERY_ENABLE_UTC = True
    CELERY_TASK_TRACK_STARTED = True
    CELERY_TASK_TIME_LIMIT = 30 * 60


# =============================================================================
# EMAIL - Hostinger en production
# =============================================================================
# Le backend email est configuré dans base.py via EMAIL_BACKEND dans .env
# Pour utiliser Hostinger, définir EMAIL_BACKEND=hostinger dans .env


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
# CAPTCHA CONFIGURATION - CloudFlare Turnstile (recommandé)
# =============================================================================
# CloudFlare Turnstile (gratuit illimité, meilleur UX que reCAPTCHA)
TURNSTILE_SITE_KEY = os.environ.get('TURNSTILE_SITE_KEY', '')
TURNSTILE_SECRET_KEY = os.environ.get('TURNSTILE_SECRET_KEY', '')

# Google reCAPTCHA v3 (legacy - à désactiver après migration vers Turnstile)
RECAPTCHA_PUBLIC_KEY = os.environ.get('RECAPTCHA_PUBLIC_KEY', '')
RECAPTCHA_PRIVATE_KEY = os.environ.get('RECAPTCHA_PRIVATE_KEY', '')
RECAPTCHA_REQUIRED_SCORE = float(os.environ.get('RECAPTCHA_REQUIRED_SCORE', 0.5))


# =============================================================================
# STATIC FILES - WhiteNoise pour Render
# =============================================================================
# Django 4.2+ utilise STORAGES au lieu de STATICFILES_STORAGE (deprecated/supprimé en 6.x)
#
# Jazzmin embarque des CSS Bootswatch qui référencent des .map inexistants.
# WhiteNoise lève MissingFileError pendant post_process (son propre check,
# pas celui de Django). On override post_process pour ignorer ces erreurs.
import logging as _logging
from whitenoise.storage import (
    CompressedManifestStaticFilesStorage as _WhiteNoiseBase,
    MissingFileError as _MissingFileError,
)

class _SafeWhiteNoiseStorage(_WhiteNoiseBase):
    manifest_strict = False

    def post_process(self, *args, **kwargs):
        _log = _logging.getLogger('whitenoise.storage')
        for entry in super().post_process(*args, **kwargs):
            name, hashed_name, processed = entry
            if isinstance(processed, Exception):
                _log.warning('Ignoring post-process error for %s: %s', name, processed)
                yield name, hashed_name, True  # report success → collectstatic won't crash
                continue
            yield entry

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "gestion_eebc.settings.prod._SafeWhiteNoiseStorage",
    },
}

# WhiteNoise middleware (doit être après SecurityMiddleware)
MIDDLEWARE.insert(2, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Optionnel: AWS S3 pour les médias
# AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
# AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
# AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')
# AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'eu-west-3')
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'


# =============================================================================
# LOGGING - Sentry en production
# =============================================================================
SENTRY_DSN = os.environ.get('SENTRY_DSN', '')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment='production',
    )

# En production sur Render, le filesystem est éphémère.
# On utilise uniquement le handler console (stdout/stderr capturé par Render).
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
