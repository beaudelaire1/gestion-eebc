#!/usr/bin/env bash
# =============================================================================
# Script de build pour Render - Gestion EEBC
# =============================================================================

set -o errexit

echo "=== Installation des dépendances ==="
pip install --upgrade pip
pip install -r requirements/prod.txt

echo "=== Collecte des fichiers statiques ==="
python manage.py collectstatic --noinput

echo "=== Application des migrations ==="
python manage.py migrate --noinput

echo "=== Initialisation des données (sites, etc.) ==="
python manage.py setup_sites

echo "=== Build terminé avec succès ==="
