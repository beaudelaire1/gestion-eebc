#!/usr/bin/env bash
# =============================================================================
# Démarrage Render - Gestion EEBC
# =============================================================================

set -o errexit
set -o nounset
set -o pipefail

PORT="${PORT:-10000}"
WORKERS="${WEB_CONCURRENCY:-2}"
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-gestion_eebc.settings.prod}"

# Backward-compatible migration path for existing Render services created
# before REDIS_URL was introduced. The Celery broker is already a shared
# Redis-compatible Render Key Value, so it is valid to reuse it for Django's
# shared cache until the Blueprint has been resynchronised.
if [[ -z "${REDIS_URL:-}" && -n "${CELERY_BROKER_URL:-}" ]]; then
    export REDIS_URL="${CELERY_BROKER_URL}"
    echo "REDIS_URL absent: utilisation du Redis CELERY_BROKER_URL existant."
fi

if [[ -z "${REDIS_URL:-}" ]]; then
    echo "ERREUR: REDIS_URL (ou CELERY_BROKER_URL Redis) est requis en production." >&2
    exit 1
fi

if [[ -z "${CLOUDINARY_URL:-}" ]]; then
    echo "ERREUR: CLOUDINARY_URL est requis en production pour les médias persistants." >&2
    exit 1
fi

echo "=== Préflight production ==="
echo "Python: $(python --version 2>&1)"
echo "Port: ${PORT}"
echo "Workers: ${WORKERS}"
echo "Settings: ${DJANGO_SETTINGS_MODULE}"

# Fail before Gunicorn if settings, cache, storage or other production
# invariants are invalid. Do not swallow startup exceptions.
python manage.py check --deploy --fail-level ERROR

# Verify Django can fully initialise with the production configuration.
python - <<'PY'
import django

django.setup()
print('Django setup OK')
PY

echo "=== Démarrage Gunicorn ==="
exec gunicorn gestion_eebc.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers "${WORKERS}" \
    --worker-class gthread \
    --threads 2 \
    --timeout 120 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
