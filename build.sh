#!/usr/bin/env bash
# =============================================================================
# Script de build pour Render - Gestion EEBC
# =============================================================================

set -o errexit

echo "=== Création des répertoires nécessaires ==="
mkdir -p logs
mkdir -p media

echo "=== Installation des dépendances système (WeasyPrint/PDF) ==="
if command -v apt-get &> /dev/null; then
    apt-get update -qq && apt-get install -y -qq --no-install-recommends \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf2.0-0 \
        libffi-dev \
        shared-mime-info \
        2>/dev/null || echo "⚠ Certaines libs système manquantes — PDF limité"
fi

echo "=== Installation des dépendances Python ==="
pip install --upgrade pip
pip install -r requirements/prod.txt

echo "=== Collecte des fichiers statiques ==="
python manage.py collectstatic --noinput

echo "=== Application des migrations ==="
python manage.py migrate --noinput

echo "=== Initialisation des données (sites, etc.) ==="
python manage.py setup_sites

echo "=== Vérification que Django démarre correctement ==="
python -c "
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_eebc.settings.prod')
django.setup()
from django.core.wsgi import get_wsgi_application
app = get_wsgi_application()
print('✓ WSGI app loaded OK')
"

echo "=== Rendre les scripts exécutables ==="
chmod +x start.sh
chmod +x build.sh

echo "=== Build terminé avec succès ==="
