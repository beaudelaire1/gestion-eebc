#!/usr/bin/env bash
# =============================================================================
# Build Render - Gestion EEBC
# =============================================================================
# A build prepares an immutable application artifact only. It must not depend
# on runtime services such as PostgreSQL, Redis, Cloudinary, SMTP or Celery.
# Runtime production invariants are enforced by settings.prod/start.sh.
# =============================================================================

set -o errexit
set -o nounset
set -o pipefail

export DJANGO_SETTINGS_MODULE="gestion_eebc.settings.build"

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

echo "=== Vérification Django (build) ==="
python manage.py check --fail-level ERROR

echo "=== Collecte des fichiers statiques ==="
python manage.py collectstatic --noinput

echo "=== Build terminé ==="
