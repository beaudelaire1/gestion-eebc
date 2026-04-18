"""
Django settings - Développement
"""

from .base import *

# =============================================================================
# DEBUG
# =============================================================================
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

# =============================================================================
# CORS - Autoriser toutes les origines en dev (Flutter web ports aléatoires)
# =============================================================================
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_ALL_ORIGINS = True


# =============================================================================
# DATABASE - SQLite pour le développement
# =============================================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# =============================================================================
# DEBUG TOOLBAR (optionnel)
# =============================================================================
try:
    import debug_toolbar
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1']
except ImportError:
    pass


# =============================================================================
# EMAIL - Console en développement (sauf si EMAIL_BACKEND est défini en env)
# =============================================================================
import os
_email_backend = os.environ.get('EMAIL_BACKEND', '')
if not _email_backend or _email_backend == 'console':
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# Sinon, on garde la valeur définie dans base.py (smtp, hostinger, etc.)


# =============================================================================
# CELERY - Exécution synchrone en dev (pas besoin de Redis)
# =============================================================================
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True


# =============================================================================
# STRIPE - Mode test
# =============================================================================
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY', '')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
# STRIPE_SUCCESS_URL = os.environ.get('STRIPE_SUCCESS_URL', 'https://eglise-ebc.org/don/succes/')
 # STRIPE_CANCEL_URL = os.environ.get('STRIPE_CANCEL_URL', 'https://eglise-ebc.org/don/annule/')
# Localhost (ancien):
STRIPE_SUCCESS_URL = 'http://localhost:8000/don/succes/'
STRIPE_CANCEL_URL = 'http://localhost:8000/don/annule/'


# =============================================================================
# TWILIO - Chargé depuis .env si disponible, sinon désactivé
# =============================================================================
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER', '')

# =============================================================================
# META WHATSAPP CLOUD API - Chargé depuis .env si disponible
# =============================================================================
META_WHATSAPP_ACCESS_TOKEN = os.environ.get('META_WHATSAPP_ACCESS_TOKEN', '')
META_WHATSAPP_PHONE_NUMBER_ID = os.environ.get('META_WHATSAPP_PHONE_NUMBER_ID', '')
META_WHATSAPP_VERIFY_TOKEN = os.environ.get('META_WHATSAPP_VERIFY_TOKEN', '')
META_WHATSAPP_APP_SECRET = os.environ.get('META_WHATSAPP_APP_SECRET', '')
META_WHATSAPP_API_VERSION = os.environ.get('META_WHATSAPP_API_VERSION', 'v23.0')


# =============================================================================
# LOGGING - Verbose en développement
# =============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}


# =============================================================================
# CAPTCHA - Clés de test Cloudflare Turnstile (widget visible, toujours valide)
# https://developers.cloudflare.com/turnstile/troubleshooting/testing/
# =============================================================================
TURNSTILE_SITE_KEY = '1x00000000000000000000AA'
TURNSTILE_SECRET_KEY = '1x0000000000000000000000000000000AA'
RECAPTCHA_PUBLIC_KEY = ''
RECAPTCHA_PRIVATE_KEY = ''
