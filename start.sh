#!/usr/bin/env bash
# =============================================================================
# Script de démarrage pour Render - Gestion EEBC
# =============================================================================
# IMPORTANT : PAS de --preload !
# Avec --preload, gunicorn charge l'app AVANT d'ouvrir le port.
# Si un import échoue (ex: librairie C manquante), le port n'est jamais
# ouvert et Render affiche "No open HTTP ports detected on 0.0.0.0".
# Sans --preload, gunicorn bind le port d'abord, puis charge l'app dans
# chaque worker. Le port est visible immédiatement par Render.
# =============================================================================

set -o errexit

# Port : utiliser PORT de Render, sinon fallback 10000 (default Render Free tier)
PORT="${PORT:-10000}"
WORKERS="${WEB_CONCURRENCY:-2}"

echo "=== Configuration Gunicorn ==="
echo "PORT: $PORT"
echo "WORKERS: $WORKERS"
echo "PYTHON VERSION: $(python --version)"
echo "DJANGO SETTINGS: ${DJANGO_SETTINGS_MODULE:-gestion_eebc.settings.prod}"

# Vérification rapide que Django se charge sans erreur fatale
echo "=== Vérification pré-démarrage ==="
python -c "
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_eebc.settings.prod')
try:
    import django
    django.setup()
    print('✓ Django setup OK')
except Exception as e:
    print(f'⚠ Django setup warning: {e}', file=sys.stderr)
    # On continue quand même — gunicorn affichera l'erreur détaillée
" || true

echo "=== Démarrage du serveur Gunicorn sur 0.0.0.0:${PORT} ==="

exec gunicorn gestion_eebc.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers "$WORKERS" \
    --worker-class gthread \
    --threads 2 \
    --timeout 120 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --log-file - \
    --log-level info \
    --access-logfile - \
    --error-logfile -
