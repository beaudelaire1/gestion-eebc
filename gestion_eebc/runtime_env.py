"""Runtime environment compatibility helpers.

Keep deployment-context detection and infrastructure aliases in one place so
every Django/Celery entry point applies the same rules before settings load.
"""

import os
import sys


STATIC_BUILD_COMMANDS = {'collectstatic'}


def is_static_asset_build() -> bool:
    """Return True only for Django commands that build static assets.

    Static asset compilation must not require runtime infrastructure such as
    PostgreSQL, Redis, Cloudinary or SMTP. Runtime commands (migrate, shell,
    custom management commands, Gunicorn/Celery bootstrap, etc.) are never
    classified as build-only operations.
    """

    return len(sys.argv) > 1 and sys.argv[1] in STATIC_BUILD_COMMANDS


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
