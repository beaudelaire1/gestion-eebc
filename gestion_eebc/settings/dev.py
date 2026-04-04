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
# EMAIL - Console en développement
# =============================================================================
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


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
# TWILIO - Désactivé en dev
# =============================================================================
TWILIO_ACCOUNT_SID = ''
TWILIO_AUTH_TOKEN = ''
TWILIO_PHONE_NUMBER = ''
TWILIO_WHATSAPP_NUMBER = ''

# =============================================================================
# META WHATSAPP CLOUD API - Désactivé en dev
# =============================================================================
META_WHATSAPP_ACCESS_TOKEN = ''
META_WHATSAPP_PHONE_NUMBER_ID = ''
META_WHATSAPP_VERIFY_TOKEN = ''
META_WHATSAPP_APP_SECRET = ''
META_WHATSAPP_API_VERSION = 'v23.0'


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
# CAPTCHA - Désactivé en dev (Turnstile nécessite un domaine autorisé)
# =============================================================================
TURNSTILE_SITE_KEY = ''
TURNSTILE_SECRET_KEY = ''
RECAPTCHA_PUBLIC_KEY = ''
RECAPTCHA_PRIVATE_KEY = ''
