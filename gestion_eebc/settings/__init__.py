# =============================================================================
# GESTION EEBC - Configuration Django
# =============================================================================
#
# Utilisation :
#   - Développement : DJANGO_SETTINGS_MODULE=gestion_eebc.settings.dev
#   - Production    : DJANGO_SETTINGS_MODULE=gestion_eebc.settings.prod
#
# Par défaut, charge les settings de développement
# =============================================================================

import os

env = os.environ.get('DJANGO_ENV', 'dev')

if env == 'prod':
    from .prod import *
elif env == 'test':
    from .test import *
else:
    from .dev import *
