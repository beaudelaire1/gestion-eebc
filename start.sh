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
