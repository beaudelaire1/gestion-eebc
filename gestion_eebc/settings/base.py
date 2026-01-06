"""
Django settings - Configuration de base (commune à tous les environnements)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Charger les variables d'environnement
load_dotenv(BASE_DIR / '.env')

# Secret Key
import secrets
SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_urlsafe(50))

# Allowed Hosts
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


# =============================================================================
# APPLICATIONS
# =============================================================================
INSTALLED_APPS = [
    # Jazzmin - doit être AVANT django.contrib.admin
    'jazzmin',
    
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    # Third party apps
    'django_htmx',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_filters',
    
    # Local apps
    'apps.core',
    'apps.accounts',
    'apps.members',
    'apps.departments',
    'apps.transport',
    'apps.inventory',
    'apps.campaigns',
    'apps.bibleclub',
    'apps.events',
    'apps.groups',
    'apps.communication',
    'apps.dashboard',
    'apps.finance',
    'apps.worship',
]


# =============================================================================
# MIDDLEWARE
# =============================================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',  # Must be before SessionTimeoutMiddleware
    'apps.accounts.middleware.ForcePasswordChangeMiddleware',
    'apps.core.middleware.SessionTimeoutMiddleware',  # Session timeout middleware
    'apps.core.middleware.RateLimitMiddleware',  # Rate limiting middleware
    'apps.core.signals.AuditMiddleware',  # Audit logging middleware
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]


# =============================================================================
# SESSION TIMEOUT CONFIGURATION
# =============================================================================
# Duration of inactivity before session expires (in minutes)
SESSION_TIMEOUT_MINUTES = int(os.environ.get('SESSION_TIMEOUT_MINUTES', 30))

# Paths excluded from session timeout tracking (e.g., API heartbeat endpoints)
SESSION_TIMEOUT_EXCLUDED_PATHS = [
    '/api/heartbeat/',
    '/static/',
    '/media/',
]


# =============================================================================
# RATE LIMITING CONFIGURATION
# =============================================================================
# Maximum number of requests allowed per window
RATE_LIMIT_REQUESTS = int(os.environ.get('RATE_LIMIT_REQUESTS', 100))

# Time window in seconds for rate limiting
RATE_LIMIT_WINDOW = int(os.environ.get('RATE_LIMIT_WINDOW', 60))

# Paths excluded from rate limiting
RATE_LIMIT_EXCLUDED_PATHS = [
    '/static/',
    '/media/',
    '/admin/jsi18n/',
]


# =============================================================================
# URLS & WSGI
# =============================================================================
ROOT_URLCONF = 'gestion_eebc.urls'
WSGI_APPLICATION = 'gestion_eebc.wsgi.application'


# =============================================================================
# TEMPLATES
# =============================================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.bibleclub.permissions.bibleclub_context',
            ],
        },
    },
]


# =============================================================================
# PASSWORD VALIDATION
# =============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# =============================================================================
# AUTHENTICATION
# =============================================================================
AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard:home'
LOGOUT_REDIRECT_URL = 'public:home'


# =============================================================================
# INTERNATIONALIZATION
# =============================================================================
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'America/Cayenne'
USE_I18N = True
USE_TZ = True


# =============================================================================
# STATIC & MEDIA FILES
# =============================================================================
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'


# =============================================================================
# DEFAULT PRIMARY KEY
# =============================================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# =============================================================================
# CRISPY FORMS
# =============================================================================
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"


# =============================================================================
# SITE SETTINGS
# =============================================================================
SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000')
SITE_NAME = os.environ.get('SITE_NAME', 'EEBC')


# =============================================================================
# EMAIL SETTINGS
# =============================================================================
_email_backend = os.environ.get('EMAIL_BACKEND', 'console')
if _email_backend == 'smtp':
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
elif _email_backend == 'console':
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
elif _email_backend == 'file':
    EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
    EMAIL_FILE_PATH = BASE_DIR / 'sent_emails'
else:
    EMAIL_BACKEND = _email_backend

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@eebc-guyane.org')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')


# =============================================================================
# JAZZMIN CONFIGURATION
# =============================================================================
JAZZMIN_SETTINGS = {
    "site_title": "EEBC",
    "site_header": "EEBC",
    "site_brand": "Gestion EEBC",
    "welcome_sign": "Bienvenue sur Gestion EEBC",
    "copyright": "EEBC - Église Évangélique Baptiste de Cabassou",
    "search_model": ["accounts.User", "members.Member", "bibleclub.Child"],
    "topmenu_links": [
        {"name": "Accueil", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Site", "url": "/", "new_window": False},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "order_with_respect_to": [
        "accounts", "core", "bibleclub", "members", "events", "worship",
        "groups", "campaigns", "finance", "departments", "transport",
        "inventory", "communication",
    ],
    "icons": {
        "auth": "fas fa-users-cog",
        "accounts.User": "fas fa-user-circle",
        "core.Site": "fas fa-church",
        "bibleclub.Child": "fas fa-child",
        "members.Member": "fas fa-user-friends",
        "events.Event": "fas fa-calendar-day",
        "finance.FinancialTransaction": "fas fa-exchange-alt",
        "groups.Group": "fas fa-users",
        "departments.Department": "fas fa-sitemap",
        "transport.DriverProfile": "fas fa-id-card",
        "inventory.Equipment": "fas fa-tools",
    },
    "related_modal_active": True,
    "custom_css": "css/admin_custom.css",
    "changeform_format": "horizontal_tabs",
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "brand_colour": "navbar-primary",
    "accent": "accent-primary",
    "navbar": "navbar-primary navbar-dark",
    "navbar_fixed": True,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "theme": "default",
    "actions_sticky_top": True,
}


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'error_detailed': {
            'format': '{levelname} {asctime} {module} {funcName} {lineno} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file_error': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'error.log',
            'maxBytes': 1024*1024*10,  # 10 MB
            'backupCount': 5,
            'formatter': 'error_detailed',
        },
        'file_django': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024*1024*10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'file_security': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 1024*1024*5,  # 5 MB
            'backupCount': 10,
            'formatter': 'error_detailed',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose',
            'include_html': True,
        },
    },
    'root': {
        'handlers': ['console', 'file_django'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file_django'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file_error', 'file_security', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['file_security', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps.core.permissions': {
            'handlers': ['file_security'],
            'level': 'WARNING',
            'propagate': True,
        },
        'apps.accounts.services': {
            'handlers': ['file_security'],
            'level': 'WARNING',
            'propagate': True,
        },
        'gestion_eebc.error_views': {
            'handlers': ['file_error', 'mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}

# Créer le répertoire logs s'il n'existe pas
import os
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
