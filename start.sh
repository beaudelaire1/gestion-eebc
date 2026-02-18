#!/usr/bin/env bash
# =============================================================================
# Script de démarrage pour Render - Gestion EEBC
# Gère l'expansion de la variable PORT avec fallback robuste
# =============================================================================

set -o errexit

# Port : utiliser PORT de Render, sinon fallback 10000 (default Render Free tier)
PORT="${PORT:-10000}"

echo "=== Démarrage du serveur Gunicorn sur le port $PORT ==="

exec gunicorn gestion_eebc.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers 1 \
    --worker-class gthread \
    --threads 4 \
    --timeout 120 \
    --log-file - \
    --log-level info \
    --access-logfile - \
    --error-logfile -
