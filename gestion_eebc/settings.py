"""
Django settings for Gestion EEBC project.
ERP minimaliste pour église - Club Biblique & Calendrier Intelligent
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production-eebc-2024')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


# Application definition
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
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'gestion_eebc.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'gestion_eebc.wsgi.application'


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Custom User Model
AUTH_USER_MODEL = 'accounts.User'


# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'America/Cayenne'  # Guyane française (UTC-3)
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"


# Email settings
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND', 
    'django.core.mail.backends.console.EmailBackend'
)


# Login URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard:home'
LOGOUT_REDIRECT_URL = 'accounts:login'


# =============================================================================
# JAZZMIN CONFIGURATION - Admin moderne
# =============================================================================
JAZZMIN_SETTINGS = {
    # Titre et branding
    "site_title": "EEBC Guyane",
    "site_header": "EEBC Guyane",
    "site_brand": "Gestion EEBC",
    "site_logo": None,
    "login_logo": None,
    "site_logo_classes": "img-circle",
    "site_icon": None,
    "welcome_sign": "Bienvenue sur Gestion EEBC Guyane",
    "copyright": "EEBC Guyane - Église Évangélique Baptiste de Cayenne",
    
    # Recherche
    "search_model": ["accounts.User", "members.Member", "bibleclub.Child"],
    
    # Top menu
    "topmenu_links": [
        {"name": "Accueil", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Site", "url": "/", "new_window": False},
        {"model": "accounts.User"},
    ],
    
    # User menu
    "usermenu_links": [
        {"name": "Profil", "url": "/accounts/profile/", "new_window": False, "icon": "fas fa-user"},
        {"model": "accounts.user"},
    ],
    
    # Menu latéral
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    
    # Ordre des apps
    "order_with_respect_to": [
        "accounts",
        "bibleclub",
        "members", 
        "events",
        "groups",
        "campaigns",
        "departments",
        "transport",
        "inventory",
        "communication",
    ],
    
    # Icônes personnalisées
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        
        "accounts": "fas fa-user-shield",
        "accounts.User": "fas fa-user-circle",
        
        "bibleclub": "fas fa-bible",
        "bibleclub.AgeGroup": "fas fa-layer-group",
        "bibleclub.BibleClass": "fas fa-chalkboard-teacher",
        "bibleclub.Child": "fas fa-child",
        "bibleclub.Monitor": "fas fa-user-tie",
        "bibleclub.Session": "fas fa-calendar-check",
        "bibleclub.Attendance": "fas fa-clipboard-check",
        "bibleclub.DriverCheckIn": "fas fa-bus",
        
        "members": "fas fa-users",
        "members.Member": "fas fa-user-friends",
        
        "events": "fas fa-calendar-alt",
        "events.Event": "fas fa-calendar-day",
        "events.EventCategory": "fas fa-tags",
        "events.EventRegistration": "fas fa-user-plus",
        
        "groups": "fas fa-people-group",
        "groups.Group": "fas fa-users",
        "groups.GroupMeeting": "fas fa-handshake",
        
        "campaigns": "fas fa-hand-holding-heart",
        "campaigns.Campaign": "fas fa-bullhorn",
        "campaigns.Donation": "fas fa-donate",
        
        "departments": "fas fa-building",
        "departments.Department": "fas fa-sitemap",
        
        "transport": "fas fa-car",
        "transport.DriverProfile": "fas fa-id-card",
        "transport.TransportRequest": "fas fa-route",
        
        "inventory": "fas fa-boxes",
        "inventory.Category": "fas fa-folder",
        "inventory.Equipment": "fas fa-tools",
        
        "communication": "fas fa-comments",
        "communication.Notification": "fas fa-bell",
        "communication.Announcement": "fas fa-bullhorn",
        "communication.EmailLog": "fas fa-envelope",
        "communication.SMSLog": "fas fa-sms",
    },
    
    # Icônes par défaut
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    
    # Related Modal
    "related_modal_active": True,
    
    # UI Tweaks
    "custom_css": "css/admin_custom.css",
    "custom_js": None,
    "use_google_fonts_cdn": True,
    "show_ui_builder": False,
    
    # Change view
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {
        "accounts.user": "collapsible",
        "bibleclub.child": "horizontal_tabs",
        "members.member": "horizontal_tabs",
    },
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-primary",
    "accent": "accent-primary",
    "navbar": "navbar-primary navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    },
    "actions_sticky_top": True,
}

