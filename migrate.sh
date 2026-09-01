#!/usr/bin/env bash
# =============================================================================
# Migration one-shot - Gestion EEBC (Coolify / Docker Compose)
# =============================================================================
# Coolify lance `docker compose up -d` : la sortie du conteneur `migrate`
# n'apparait pas dans le journal de deploiement, qui se contente de
# "service migrate didn't complete successfully: exit 1".
#
# Ce script diagnostique donc lui-meme les causes d'echec previsibles
# (variables manquantes, base ou Redis injoignables) avant de laisser Django
# lever une exception brute, et il imprime la raison exacte dans les logs du
# conteneur.

set -o errexit
set -o nounset
set -o pipefail

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-gestion_eebc.settings.prod}"

# Compatibilite : une seule instance Redis peut servir le cache Django et
# Celery. Meme regle que start.sh pour eviter deux comportements differents.
if [[ -z "${REDIS_URL:-}" && -n "${CELERY_BROKER_URL:-}" ]]; then
    export REDIS_URL="${CELERY_BROKER_URL}"
fi

DB_WAIT_SECONDS="${MIGRATE_DB_WAIT_SECONDS:-90}"

fail() {
    echo "" >&2
    echo "ERREUR MIGRATION EEBC: $*" >&2
    exit 1
}

require_env() {
    local name="$1"
    local hint="$2"
    if [[ -z "${!name:-}" ]]; then
        fail "${name} est absent ou vide. ${hint}"
    fi
}

echo "=== Preflight migration EEBC ==="
echo "Python: $(python --version 2>&1)"
echo "Settings: ${DJANGO_SETTINGS_MODULE}"

require_env SECRET_KEY "Definir un secret stable d'au moins 32 caracteres dans Coolify."
require_env ALLOWED_HOSTS "Exemple: eglise-ebc.org,www.eglise-ebc.org"
require_env CSRF_TRUSTED_ORIGINS "Exemple: https://eglise-ebc.org,https://www.eglise-ebc.org"
require_env DATABASE_URL "Copier l'URL interne de la ressource PostgreSQL Coolify."
require_env REDIS_URL "Copier l'URL interne de la ressource Redis Coolify."

if [[ -z "${TRUSTED_PROXY_IPS:-}" && -z "${TRUSTED_CLIENT_IP_HEADER:-}" ]]; then
    fail "Definir TRUSTED_PROXY_IPS (CIDR reels du proxy) ou TRUSTED_CLIENT_IP_HEADER=HTTP_CF_CONNECTING_IP."
fi

# Le stockage media est valide a l'import de settings.prod : une variable
# manquante ici fait echouer `manage.py migrate` avant meme d'ouvrir une
# connexion PostgreSQL.
MEDIA_BACKEND="$(printf '%s' "${MEDIA_STORAGE_BACKEND:-cloudinary}" | tr '[:upper:]' '[:lower:]')"
echo "Stockage media: ${MEDIA_BACKEND}"

case "${MEDIA_BACKEND}" in
    cloudinary)
        require_env CLOUDINARY_URL \
            "MEDIA_STORAGE_BACKEND=cloudinary exige CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME."
        ;;
    s3)
        for name in AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_STORAGE_BUCKET_NAME \
                    AWS_S3_ENDPOINT_URL AWS_S3_REGION_NAME; do
            require_env "${name}" "MEDIA_STORAGE_BACKEND=s3 exige toutes les variables AWS_*."
        done
        ;;
    *)
        fail "MEDIA_STORAGE_BACKEND doit valoir 'cloudinary' ou 's3' (recu: '${MEDIA_BACKEND}')."
        ;;
esac

echo "Variables obligatoires: OK"

# PostgreSQL et Redis sont des ressources Coolify separees. Sans "Connect To
# Predefined Network" active des deux cotes, le nom d'hote interne ne se
# resout pas et la migration echoue instantanement.
DB_WAIT_SECONDS="${DB_WAIT_SECONDS}" python - <<'PY'
import os
import sys
import time

import django
from django.db import connections
from django.db.utils import OperationalError

django.setup()

deadline = time.monotonic() + float(os.environ.get('DB_WAIT_SECONDS', '90'))
attempt = 0
last_error = None

while True:
    attempt += 1
    try:
        connections['default'].ensure_connection()
        break
    except OperationalError as exc:
        last_error = exc
        if time.monotonic() >= deadline:
            print('', file=sys.stderr)
            print(
                'ERREUR MIGRATION EEBC: PostgreSQL injoignable via DATABASE_URL '
                f'apres {attempt} tentatives.',
                file=sys.stderr,
            )
            print(f'Detail psycopg: {exc}', file=sys.stderr)
            print(
                "Verifier l'URL interne, et activer 'Connect To Predefined Network' "
                'sur la ressource PostgreSQL Coolify ET sur cette application.',
                file=sys.stderr,
            )
            raise SystemExit(1)
        print(f'PostgreSQL indisponible (tentative {attempt}), nouvelle tentative...')
        time.sleep(3)

print(f'PostgreSQL joignable apres {attempt} tentative(s)')

from django.core.cache import cache

try:
    cache.set('eebc:migrate:preflight', '1', 30)
    cache.get('eebc:migrate:preflight')
except Exception as exc:  # noqa: BLE001 - la cause exacte doit rester lisible
    print('', file=sys.stderr)
    print(
        'ERREUR MIGRATION EEBC: Redis injoignable via REDIS_URL. '
        'Le cache partage est obligatoire pour les compteurs de securite.',
        file=sys.stderr,
    )
    print(f'Detail: {exc}', file=sys.stderr)
    raise SystemExit(1)

print('Redis joignable')
PY

echo "=== Migrations ==="
python manage.py migrate --noinput
python manage.py migrate --check

# setup_sites est un seed d'installation : il force adresse, telephone, email et
# horaires avec des valeurs codees en dur. Le rejouer sur une base qui contient
# deja des sites effacerait toute modification faite depuis l'admin.
python - <<'PYSEED'
import django

django.setup()

from apps.core.models import Site

if Site.objects.exists():
    print(f'{Site.objects.count()} site(s) deja presents : seed setup_sites ignore')
else:
    from django.core.management import call_command

    call_command('setup_sites')
PYSEED

echo "=== Migration terminee avec succes ==="
