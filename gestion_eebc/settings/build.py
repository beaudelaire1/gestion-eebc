"""Django settings used only during the immutable Render build phase.

The build must be able to install dependencies, validate imports and collect
static assets without connecting to PostgreSQL, Redis, Cloudinary or email.
Runtime production invariants remain enforced by ``settings.prod`` and
``start.sh``.
"""

from .base import *
from .csp_policy import apply_csp4

apply_csp4(globals())

DEBUG = False
SECRET_KEY = 'eebc-build-only-secret-not-used-at-runtime-2026'
ALLOWED_HOSTS = ['build.local']

# No external services are required to create the deploy artifact.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'eebc-render-build',
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# The build only emits static assets. User media is never written during the
# build and therefore deliberately stays on the local filesystem here.
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

if 'whitenoise.middleware.WhiteNoiseMiddleware' not in MIDDLEWARE:
    security_index = MIDDLEWARE.index('django.middleware.security.SecurityMiddleware')
    MIDDLEWARE.insert(security_index + 1, 'whitenoise.middleware.WhiteNoiseMiddleware')
