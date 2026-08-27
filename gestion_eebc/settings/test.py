"""
Django settings - Tests
"""
import os
from .base import *

DEBUG = False

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

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

import tempfile
MEDIA_ROOT = tempfile.mkdtemp()

STRIPE_PUBLIC_KEY = ''
STRIPE_SECRET_KEY = ''
TWILIO_ACCOUNT_SID = ''
TWILIO_AUTH_TOKEN = ''
META_WHATSAPP_ACCESS_TOKEN = ''
META_WHATSAPP_PHONE_NUMBER_ID = ''
META_WHATSAPP_VERIFY_TOKEN = ''
META_WHATSAPP_APP_SECRET = ''
META_WHATSAPP_API_VERSION = 'v23.0'

RATE_LIMIT_ENABLED = True
RATE_LIMIT_REQUESTS = 1000
RATE_LIMIT_WINDOW = 60

# Les tests métier existants utilisent massivement force_login(). L'enforcement
# transversal est désactivé ici et réactivé explicitement dans les tests sécurité.
TWO_FACTOR_ENFORCEMENT_ENABLED = False
TWO_FACTOR_ENCRYPTION_KEY = 'test-only-two-factor-encryption-key-do-not-use-in-production'
