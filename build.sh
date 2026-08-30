#!/usr/bin/env bash
# =============================================================================
# Build Render - Gestion EEBC
# =============================================================================
# A build prepares an immutable application artifact. Database mutations,
# notifications and backups belong to pre-deploy/cron phases, not here.
# =============================================================================

set -o errexit
set -o nounset
set -o pipefail

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-gestion_eebc.settings.prod}"

echo "=== Python runtime ==="
python --version

echo "=== Installation des dépendances Python ==="
python -m pip install --upgrade pip
python -m pip install -r requirements/prod.txt
python -m pip check

echo "=== Smoke test WeasyPrint ==="
python - <<'PY'
from weasyprint import HTML

pdf = HTML(string='<html><body><p>EEBC PDF runtime check</p></body></html>').write_pdf()
if not pdf.startswith(b'%PDF'):
    raise RuntimeError('WeasyPrint did not produce a valid PDF payload')
print(f'WeasyPrint OK ({len(pdf)} bytes)')
PY

echo "=== Collecte des fichiers statiques ==="
python manage.py collectstatic --noinput

echo "=== Vérification Django ==="
python manage.py check --deploy --fail-level ERROR

echo "=== Build terminé ==="
