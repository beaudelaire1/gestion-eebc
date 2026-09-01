# =============================================================================
# GESTION EEBC - Configuration Django
# =============================================================================
#
# Utilisation :
#   - Développement : DJANGO_SETTINGS_MODULE=gestion_eebc.settings.dev
#   - Production    : DJANGO_SETTINGS_MODULE=gestion_eebc.settings.prod
#   - Tests         : DJANGO_SETTINGS_MODULE=gestion_eebc.settings.test
#
# En production, utiliser DJANGO_SETTINGS_MODULE directement (pas ce fichier).
# Ce __init__.py n'est qu'un raccourci pour le développement local.
# =============================================================================

import os

settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', '')

# Si un sous-module spécifique est configuré (prod, test, dev),
# __init__.py est importé comme package intermédiaire → ne rien faire.
if settings_module and settings_module != 'gestion_eebc.settings':
    pass
else:
    env = os.environ.get('DJANGO_ENV', 'dev')

    # Sécurité : ne jamais charger les réglages de développement sur une
    # plateforme d'hébergement, reconnue à ses propres marqueurs.
    PLATFORM_MARKERS = ('COOLIFY_RESOURCE_UUID', 'COOLIFY_CONTAINER_NAME', 'COOLIFY_URL')
    if env == 'dev' and any(os.environ.get(marker) for marker in PLATFORM_MARKERS):
        raise RuntimeError(
            "DJANGO_ENV='dev' détecté sur une plateforme d'hébergement. "
            "Utilisez DJANGO_SETTINGS_MODULE=gestion_eebc.settings.prod"
        )

    if env == 'prod':
        from .prod import *  # noqa: F401,F403
    elif env == 'test':
        from .test import *  # noqa: F401,F403
    else:
        from .dev import *  # noqa: F401,F403
