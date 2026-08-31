#!/usr/bin/env bash
# =============================================================================
# Production startup - Gestion EEBC
# =============================================================================

set -o errexit
set -o nounset
set -o pipefail

PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-2}"
FORWARDED_ALLOW_IPS="${GUNICORN_FORWARDED_ALLOW_IPS:-*}"
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-gestion_eebc.settings.prod}"

# Compatibility: one shared Redis instance can serve Django cache, sessions and
# Celery. Prefer defining REDIS_URL explicitly in the deployment platform.
if [[ -z "${REDIS_URL:-}" && -n "${CELERY_BROKER_URL:-}" ]]; then
    export REDIS_URL="${CELERY_BROKER_URL}"
fi

if [[ -z "${REDIS_URL:-}" ]]; then
    echo "ERREUR: REDIS_URL (ou CELERY_BROKER_URL Redis) est requis en production." >&2
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
    --forwarded-allow-ips "${FORWARDED_ALLOW_IPS}" \
    --access-logfile - \
    --error-logfile - \
    --log-level info
