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

echo "=== Installation des dépendances système (WeasyPrint/PDF) ==="
if command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y -qq --no-install-recommends \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf2.0-0 \
        libffi-dev \
        shared-mime-info
fi

echo "=== Installation des dépendances Python ==="
python -m pip install --upgrade pip
python -m pip install -r requirements/prod.txt

echo "=== Nettoyage des sourceMappingURL cassés (Jazzmin/Bootswatch) ==="
python - <<'PY'
import pathlib
import re

try:
    import jazzmin
except ImportError:
    print('Jazzmin non installé, nettoyage ignoré')
else:
    root = pathlib.Path(jazzmin.__path__[0]) / 'static' / 'vendor' / 'bootswatch'
    if not root.exists():
        print('Répertoire Bootswatch absent, nettoyage ignoré')
    else:
        for css in root.rglob('*.css'):
            text = css.read_text(encoding='utf-8', errors='ignore')
            cleaned = re.sub(r'/\*#\s*sourceMappingURL=.*?\*/', '', text)
            cleaned = re.sub(r'//# sourceMappingURL=.*', '', cleaned)
            if cleaned != text:
                css.write_text(cleaned, encoding='utf-8')
                print(f'  Nettoyé: {css.relative_to(root)}')
PY

echo "=== Collecte des fichiers statiques ==="
python manage.py collectstatic --noinput

echo "=== Vérification Django ==="
python manage.py check --deploy --fail-level ERROR

echo "=== Build terminé ==="
