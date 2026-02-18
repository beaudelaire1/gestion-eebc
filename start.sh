#!/usr/bin/env bash
# =============================================================================
# Script de démarrage pour Render - Gestion EEBC
# Gère l'expansion de la variable PORT avec fallback robuste
# =============================================================================

set -o errexit

# Port : utiliser PORT de Render, sinon fallback 10000 (default Render Free tier)
PORT="${PORT:-10000}"
WORKERS="${WEB_CONCURRENCY:-1}"

echo "=== Configuration Gunicorn ==="
echo "PORT: $PORT"
echo "WORKERS: $WORKERS"
echo "PYTHON VERSION: $(python --version)"
echo "DJANGO SETTINGS: ${DJANGO_SETTINGS_MODULE:-gestion_eebc.settings.prod}"
echo "=== Démarrage du serveur Gunicorn ==="

exec gunicorn gestion_eebc.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers "$WORKERS" \
    --worker-class gthread \
    --threads 4 \
    --timeout 120 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --preload \
    --log-file - \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    --capture-output
