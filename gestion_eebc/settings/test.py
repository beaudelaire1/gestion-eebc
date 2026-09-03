"""
Django settings - Tests
"""
import os
import tempfile

from .base import *
from .csp_policy import apply_csp4

apply_csp4(globals())

# =============================================================================
# DEBUG
# =============================================================================
DEBUG = False

# =============================================================================
# DATABASE - PostgreSQL en CI (via DATABASE_URL), SQLite sinon
# =============================================================================
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    import dj_database_url

    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=0)
    }
else:
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
MEDIA_ROOT = tempfile.mkdtemp()

# =============================================================================
# DÉSACTIVER LES SERVICES EXTERNES
# =============================================================================
STRIPE_PUBLIC_KEY = ''
STRIPE_SECRET_KEY = ''
TWILIO_ACCOUNT_SID = ''
TWILIO_AUTH_TOKEN = ''
META_WHATSAPP_ACCESS_TOKEN = ''
META_WHATSAPP_PHONE_NUMBER_ID = ''
META_WHATSAPP_VERIFY_TOKEN = ''
META_WHATSAPP_APP_SECRET = ''
META_WHATSAPP_API_VERSION = 'v23.0'

# =============================================================================
# DOUBLE AUTHENTIFICATION (2FA)
# =============================================================================
# La contrainte d'enrôlement est désactivée par défaut pour que les tests de
# vues restent des tests de vues. Les tests qui portent sur la politique
# elle-même la réactivent explicitement via override_settings.
TWO_FACTOR_ENFORCED_FOR_PRIVILEGED_ROLES = False

# =============================================================================
# RATE LIMITING POUR LES TESTS
# =============================================================================
RATE_LIMIT_ENABLED = True
RATE_LIMIT_REQUESTS = 1000
RATE_LIMIT_WINDOW = 60
