"""
WSGI config for Gestion EEBC project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_eebc.settings')

application = get_wsgi_application()

