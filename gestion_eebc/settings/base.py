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
# CAPTCHA CONFIGURATION - Transition reCAPTCHA → CloudFlare Turnstile
# =============================================================================
# CloudFlare Turnstile (recommandé : gratuit illimité, meilleur UX)
TURNSTILE_SITE_KEY = os.environ.get('TURNSTILE_SITE_KEY', '')
TURNSTILE_SECRET_KEY = os.environ.get('TURNSTILE_SECRET_KEY', '')

# Google reCAPTCHA v3 (legacy, désactiver après migration)
RECAPTCHA_PUBLIC_KEY = os.environ.get('RECAPTCHA_PUBLIC_KEY', '')
RECAPTCHA_PRIVATE_KEY = os.environ.get('RECAPTCHA_PRIVATE_KEY', '')

# =============================================================================
# DEBUG (défaut False, overrideé par dev.py/prod.py)
# =============================================================================
DEBUG = False

# =============================================================================
# APPLICATIONS
# =============================================================================
INSTALLED_APPS = [
    # Thème admin Django (doit être avant django.contrib.admin)
    'jazzmin',

    # Interface d'administration Django standard
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sitemaps',
    
    # Third party apps
    'django_htmx',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_filters',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    
    # Local apps
    'apps.core',
    'apps.public',
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
    'apps.imports',  # Import Excel pour membres et enfants
    'apps.api',  # API REST pour application mobile
    'apps.young',  # Module Jeunesse
    'apps.documents',  # Documents & Médias
]


# =============================================================================
# MIDDLEWARE
# =============================================================================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
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
    'csp.middleware.CSPMiddleware',  # Content Security Policy
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
# SECURITY CONFIGURATION
# =============================================================================

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    "https://eebc.org",
    "https://www.eebc.org",
    "https://eglise-ebc.org",
    "https://www.eglise-ebc.org",
]

# Dev-only origins (localhost, Expo, Metro)
if DEBUG:
    CORS_ORIGIN_ALLOW_ALL = True
    CORS_ALLOWED_ORIGINS += [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
else:
    CORS_ORIGIN_ALLOW_ALL = False

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'hx-request',
    'hx-target',
    'hx-current-url',
]

# Content Security Policy
CSP_DEFAULT_SRC = ["'self'"]
CSP_SCRIPT_SRC = [
    "'self'",
    "'unsafe-inline'",  # Nécessaire pour HTMX et Bootstrap
    "https://cdn.jsdelivr.net",
    "https://unpkg.com",
    "https://challenges.cloudflare.com",
]
CSP_STYLE_SRC = [
    "'self'",
    "'unsafe-inline'",
    "https://cdn.jsdelivr.net",
    "https://fonts.googleapis.com",
]
CSP_FONT_SRC = [
    "'self'",
    "https://fonts.gstatic.com",
    "https://cdn.jsdelivr.net",
]
CSP_IMG_SRC = ["'self'", "data:", "https:"]
CSP_CONNECT_SRC = ["'self'", "https://challenges.cloudflare.com"]
CSP_FRAME_SRC = ["'self'", "https://challenges.cloudflare.com", "https://js.stripe.com"]

# Security Headers
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# Permissions Policy
PERMISSIONS_POLICY = {
    "geolocation": [],
    "microphone": [],
    "camera": [],
}

# =============================================================================
# SESSION & CSRF SECURITY
# =============================================================================
SESSION_COOKIE_HTTPONLY = True  # S2: Prevent JavaScript access to session cookie
SESSION_COOKIE_SAMESITE = 'Strict'  # S2: CSRF protection
SESSION_COOKIE_SECURE = False  # Overridden to True in prod.py
CSRF_COOKIE_HTTPONLY = True  # S2: Secure CSRF token
CSRF_COOKIE_SAMESITE = 'Strict'  # S2: CSRF protection
CSRF_COOKIE_SECURE = False  # Overridden to True in prod.py
X_FRAME_OPTIONS = 'DENY'  # S3: Prevent clickjacking - deny all iframe embedding


# =============================================================================
# BUSINESS LOGIC CONFIGURATION
# =============================================================================

# Seuils et limites métier
MEMBER_VISIT_THRESHOLD_DAYS = int(os.environ.get('MEMBER_VISIT_THRESHOLD_DAYS', 180))  # 6 mois
RECURRING_ABSENCE_THRESHOLD = int(os.environ.get('RECURRING_ABSENCE_THRESHOLD', 3))
ROLE_ASSIGNMENT_EXPIRY_HOURS = int(os.environ.get('ROLE_ASSIGNMENT_EXPIRY_HOURS', 48))

# Validation des données
ALLOWED_EMAIL_DOMAINS = os.environ.get('ALLOWED_EMAIL_DOMAINS', '').split(',') if os.environ.get('ALLOWED_EMAIL_DOMAINS') else None
MAX_FINANCIAL_AMOUNT = float(os.environ.get('MAX_FINANCIAL_AMOUNT', 1000000))  # 1M€

# Notifications
DEFAULT_NOTIFICATION_DAYS_BEFORE = int(os.environ.get('DEFAULT_NOTIFICATION_DAYS_BEFORE', 4))
DEFAULT_NOTIFICATION_DAY = int(os.environ.get('DEFAULT_NOTIFICATION_DAY', 3))  # Mercredi

# Pagination
DEFAULT_PAGE_SIZE = int(os.environ.get('DEFAULT_PAGE_SIZE', 25))
MAX_PAGE_SIZE = int(os.environ.get('MAX_PAGE_SIZE', 100))


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
STATICFILES_DIRS = [
    BASE_DIR / 'static',
    BASE_DIR / 'images',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Upload : taille max pour fichiers audio/vidéo (500 Mo)
FILE_UPLOAD_MAX_MEMORY_SIZE = 500 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 500 * 1024 * 1024


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
elif _email_backend == 'hostinger':
    EMAIL_BACKEND = 'apps.core.infrastructure.hostinger_email_backend.HostingerEmailBackend'
elif _email_backend == 'console':
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
elif _email_backend == 'file':
    EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
    EMAIL_FILE_PATH = BASE_DIR / 'sent_emails'
else:
    EMAIL_BACKEND = _email_backend

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', '') or os.environ.get('HOSTINGER_EMAIL_HOST_USER', 'noreply@eglise-ebc.org')

# Configuration SMTP standard (Gmail, Outlook, etc.)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# Configuration Hostinger Email
HOSTINGER_API_KEY = os.environ.get('HOSTINGER_API_KEY', '')
HOSTINGER_EMAIL_HOST = os.environ.get('HOSTINGER_EMAIL_HOST', 'smtp.hostinger.com')
HOSTINGER_EMAIL_PORT = int(os.environ.get('HOSTINGER_EMAIL_PORT', 587))
HOSTINGER_EMAIL_USE_TLS = os.environ.get('HOSTINGER_EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
HOSTINGER_EMAIL_USE_SSL = os.environ.get('HOSTINGER_EMAIL_USE_SSL', 'False').lower() in ('true', '1', 'yes')
HOSTINGER_EMAIL_HOST_USER = os.environ.get('HOSTINGER_EMAIL_HOST_USER', '')
HOSTINGER_EMAIL_HOST_PASSWORD = os.environ.get('HOSTINGER_EMAIL_HOST_PASSWORD', '')

# Configuration avancée Hostinger
HOSTINGER_EMAIL_TIMEOUT = int(os.environ.get('HOSTINGER_EMAIL_TIMEOUT', 30))
HOSTINGER_EMAIL_MAX_RETRIES = int(os.environ.get('HOSTINGER_EMAIL_MAX_RETRIES', 3))
HOSTINGER_API_BASE_URL = os.environ.get('HOSTINGER_API_BASE_URL', 'https://developers.hostinger.com')


# =============================================================================
# ADMIN CONFIGURATION
# =============================================================================
# Admin Django standard - simple et robuste
ADMIN_SITE_HEADER = "EEBC - Gestion"
ADMIN_SITE_TITLE = "EEBC Admin"
ADMIN_INDEX_TITLE = "Tableau de bord"

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


# =============================================================================
# DJANGO REST FRAMEWORK CONFIGURATION
# =============================================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': DEFAULT_PAGE_SIZE,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
    'EXCEPTION_HANDLER': 'apps.api.exceptions.custom_exception_handler',
}


# =============================================================================
# SIMPLE JWT CONFIGURATION
# =============================================================================
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    
    'JTI_CLAIM': 'jti',
    
    'TOKEN_OBTAIN_SERIALIZER': 'apps.api.serializers.CustomTokenObtainPairSerializer',
}


# =============================================================================
# MOBILE API CONFIGURATION
# =============================================================================
# Maximum failed login attempts before lockout
API_MAX_LOGIN_ATTEMPTS = int(os.environ.get('API_MAX_LOGIN_ATTEMPTS', 5))

# Lockout duration in minutes
API_LOCKOUT_DURATION_MINUTES = int(os.environ.get('API_LOCKOUT_DURATION_MINUTES', 15))

# CORS settings for mobile app (dev only)
if DEBUG:
    CORS_ALLOWED_ORIGINS += [
        "http://localhost:19006",  # Expo development
        "http://localhost:8081",   # Metro bundler
    ]
# =============================================================================
# JAZZMIN ADMIN CONFIGURATION
# =============================================================================
# Jazzmin theme and UI customization
JAZZMIN_SETTINGS = {
    "site_title": "EEBC Admin",
    "site_header": "Gestion Église Baptiste de Cayenne",
    "site_brand": "EEBC",
    
    # Navigation customization
    "navigation_expanded": False,
    "show_sidebar": True,
    "navigation_depth": 2,
    
    # UI customizations
    "show_ui_builder": False,
    "default_icon_parents": "fas fa-chevron-right",
    "default_icon_children": "fas fa-arrow-right",
    
    # Search
    "search_model": ["auth.User"],
    
    # Icons configuration
    "icons": {
        "auth": "fas fa-users",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "accounts.User": "fas fa-user-circle",
        "members.Member": "fas fa-id-card",
        "members.LifeEvent": "fas fa-birthday-cake",
        "members.VisitationLog": "fas fa-clipboard",
        "departments.Department": "fas fa-sitemap",
        "transport.Vehicle": "fas fa-car",
        "transport.TransportRequest": "fas fa-route",
        "inventory.Category": "fas fa-tags",
        "inventory.Equipment": "fas fa-tools",
        "campaigns.Campaign": "fas fa-dollar-sign",
        "campaigns.Donation": "fas fa-donate",
        "communication.Message": "fas fa-envelope",
        "communication.Newsletter": "fas fa-newspaper",
        "events.Event": "fas fa-calendar",
        "events.EventCategory": "fas fa-list",
        "finance.Budget": "fas fa-chart-pie",
        "finance.BudgetLine": "fas fa-chart-bar",
        "finance.FinancialTransaction": "fas fa-exchange-alt",
        "worship.WorshipService": "fas fa-church",
        "worship.ServiceRole": "fas fa-user-tie",
        "groups.Group": "fas fa-users-circle",
        "groups.GroupMeeting": "fas fa-video",
        "bibleclub.BibleStudy": "fas fa-book",
        "dashboard.Dashboard": "fas fa-chart-line",
    },
    
    # Related modal widget customization
    "related_modal_active": True,
    "show_form_bottom_submit_button": True,
    "show_administration_panel": True,
    "enable_nav_sidebar": True,
    
    # Custom theme colors
    "changeform_format": "collapsible",
    "changeform_format_overrides": {
        "auth.user": "collapsible",
        "auth.group": "collapsible",
    },
}

# =============================================================================
# JAZZMIN UI TWEAKS
# =============================================================================
# Fix for inline display issues in Jazzmin
TEMPLATES[0]['OPTIONS']['context_processors'] = TEMPLATES[0]['OPTIONS'].get('context_processors', [])
if 'django.template.context_processors.request' not in TEMPLATES[0]['OPTIONS']['context_processors']:
    TEMPLATES[0]['OPTIONS']['context_processors'].append('django.template.context_processors.request')
if 'django.contrib.auth.context_processors.auth' not in TEMPLATES[0]['OPTIONS']['context_processors']:
    TEMPLATES[0]['OPTIONS']['context_processors'].append('django.contrib.auth.context_processors.auth')