import os
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]


def _clean_env(settings_module='gestion_eebc.settings.prod'):
    env = os.environ.copy()
    for key in (
        'REDIS_URL',
        'CELERY_BROKER_URL',
        'CELERY_RESULT_BACKEND',
        'DATABASE_URL',
        'DB_NAME',
        'DB_USER',
        'DB_PASSWORD',
        'DB_HOST',
        'CLOUDINARY_URL',
        'ALLOWED_HOSTS',
        'SECRET_KEY',
        'SENTRY_DSN',
    ):
        # Prevent settings/base.py from reloading a developer value from .env.
        env[key] = ''
    env['DJANGO_SETTINGS_MODULE'] = settings_module
    return env


def test_collectstatic_with_build_settings_does_not_require_runtime_services():
    result = subprocess.run(
        [sys.executable, 'manage.py', 'collectstatic', '--noinput', '--dry-run'],
        cwd=BASE_DIR,
        env=_clean_env('gestion_eebc.settings.build'),
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert 'REDIS_URL is required in production' not in result.stderr
    assert 'Production security requires a shared cache' not in result.stderr


def test_runtime_command_without_redis_is_rejected():
    env = _clean_env()
    env.update(
        {
            'SECRET_KEY': 'ci-runtime-secret-key-long-enough-and-stable-2026',
            'ALLOWED_HOSTS': 'localhost',
            'DATABASE_URL': 'sqlite:///:memory:',
            'CLOUDINARY_URL': 'cloudinary://ci_key:ci_secret@ci_cloud',
            'TRUSTED_CLIENT_IP_HEADER': 'HTTP_CF_CONNECTING_IP',
        }
    )

    result = subprocess.run(
        [sys.executable, 'manage.py', 'check'],
        cwd=BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode != 0
    assert 'REDIS_URL is required in production' in (result.stdout + result.stderr)
