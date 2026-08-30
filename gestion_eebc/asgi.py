"""
ASGI config for Gestion EEBC project.
"""

import os

from django.core.asgi import get_asgi_application

from .runtime_env import normalize_runtime_environment

normalize_runtime_environment()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_eebc.settings.prod')

application = get_asgi_application()
