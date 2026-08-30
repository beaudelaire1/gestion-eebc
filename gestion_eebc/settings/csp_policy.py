"""Shared Content Security Policy configuration for every environment."""

from csp.constants import NONE, SELF, UNSAFE_INLINE


LEGACY_CSP_SETTINGS = (
    'CSP_DEFAULT_SRC',
    'CSP_SCRIPT_SRC',
    'CSP_STYLE_SRC',
    'CSP_FONT_SRC',
    'CSP_IMG_SRC',
    'CSP_CONNECT_SRC',
    'CSP_FRAME_SRC',
)

CONTENT_SECURITY_POLICY = {
    'DIRECTIVES': {
        'default-src': [SELF],
        'script-src': [
            SELF,
            UNSAFE_INLINE,
            'https://cdn.jsdelivr.net',
            'https://unpkg.com',
            'https://challenges.cloudflare.com',
            'https://js.stripe.com',
        ],
        'style-src': [
            SELF,
            UNSAFE_INLINE,
            'https://cdn.jsdelivr.net',
            'https://fonts.googleapis.com',
        ],
        'font-src': [
            SELF,
            'https://fonts.gstatic.com',
            'https://cdn.jsdelivr.net',
        ],
        'img-src': [SELF, 'data:', 'https:'],
        'media-src': [SELF, 'https:'],
        'connect-src': [
            SELF,
            'https://challenges.cloudflare.com',
            'https://api.stripe.com',
        ],
        'frame-src': [
            SELF,
            'https://challenges.cloudflare.com',
            'https://js.stripe.com',
            'https://hooks.stripe.com',
        ],
        'object-src': [NONE],
        'base-uri': [SELF],
        'frame-ancestors': [NONE],
    }
}


def apply_csp4(settings_namespace: dict) -> None:
    """Replace inherited django-csp <=3 settings with the v4 configuration."""
    for setting_name in LEGACY_CSP_SETTINGS:
        settings_namespace.pop(setting_name, None)

    installed_apps = settings_namespace['INSTALLED_APPS']
    if 'csp' not in installed_apps:
        installed_apps.insert(installed_apps.index('django.contrib.staticfiles'), 'csp')

    settings_namespace['CONTENT_SECURITY_POLICY'] = CONTENT_SECURITY_POLICY
