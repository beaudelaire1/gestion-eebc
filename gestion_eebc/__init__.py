# Gestion EEBC - Main Project Package

# Import Celery app pour Django
from .celery import app as celery_app

__all__ = ('celery_app',)
