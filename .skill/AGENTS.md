# AGENTS.md

## Mission
Travailler sur ce dépôt sans casser les flux existants.

## Stack
- Django
- HTMX
- Alpine.js
- PostgreSQL
- WeasyPrint

## Lire d'abord
- README.md
- LIRE_DABORD.md
- requirements.txt
- requirements/base.txt
- gestion_eebc/settings/base.py
- gestion_eebc/settings/dev.py
- gestion_eebc/settings/prod.py
- apps/*/models.py
- apps/*/views.py
- templates/
- conftest.py
- render.yaml

## Commandes
- Tests : pytest
- Lint : ruff check .
- Format : ruff format .
- Run : python manage.py runserver

## Règles du repo
- Ne jamais introduire React.
- Préserver les conventions Django existantes.
- Toute modification métier doit vérifier permissions, validations et impacts admin.
- Toute vue modifiée doit être vérifiée côté sécurité et performance.
- Limiter le rayon d’impact des refactors.

## Livraison attendue
Toujours répondre avec :
1. compréhension du besoin
2. fichiers touchés
3. changements réalisés
4. validations faites
5. risques restants