"""Runtime environment compatibility helpers.

Keep infrastructure aliases in one place so every Django/Celery entry point
sees the same production environment before settings are imported.
"""

import os


def normalize_runtime_environment() -> None:
    """Map the legacy Celery Redis URL to Django's shared REDIS_URL.

    Older Render services already expose CELERY_BROKER_URL from the same
    Redis-compatible Key Value instance but do not yet expose REDIS_URL.
    Reusing that URL preserves the production requirement for a shared cache
    without falling back to process-local memory.
    """

    if os.environ.get('REDIS_URL', '').strip():
        return

    broker_url = os.environ.get('CELERY_BROKER_URL', '').strip()
    if broker_url.startswith(('redis://', 'rediss://')):
        os.environ['REDIS_URL'] = broker_url
