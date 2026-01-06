"""
Django settings - Tests
"""

from .base import *

# =============================================================================
# DEBUG
# =============================================================================
DEBUG = False


# =============================================================================
# DATABASE - SQLite en mémoire pour les tests
# =============================================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}


# =============================================================================
# PASSWORD HASHERS - Plus rapide pour les tests
# =============================================================================
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]


# =============================================================================
# EMAIL - En mémoire
# =============================================================================
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'


# =============================================================================
# CELERY - Synchrone pour les tests
# =============================================================================
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True


# =============================================================================
# CACHE - Local memory
# =============================================================================
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}


# =============================================================================
# MEDIA - Temporaire
# =============================================================================
import tempfile
MEDIA_ROOT = tempfile.mkdtemp()


# =============================================================================
# DÉSACTIVER LES SERVICES EXTERNES
# =============================================================================
STRIPE_PUBLIC_KEY = ''
STRIPE_SECRET_KEY = ''
TWILIO_ACCOUNT_SID = ''
TWILIO_AUTH_TOKEN = ''


# =============================================================================
# RATE LIMITING POUR LES TESTS
# =============================================================================
# Enable rate limiting for tests but with very high limits to avoid interference
RATE_LIMIT_ENABLED = True
RATE_LIMIT_REQUESTS = 1000  # Very high limit to avoid blocking other tests
RATE_LIMIT_WINDOW = 60  # 1 minute window
