# AGENTS.md

## Mission
Travailler dans ce dépôt EEBC avec des changements ciblés, vérifiables et compatibles avec les flux Django, HTMX et Flutter existants. Pour les audits, produire des constats sourcés, priorisés et actionnables avant toute proposition de refactor.

## Lire D'abord
- Vue d'ensemble : [README.md](README.md), [LIRE_DABORD.md](LIRE_DABORD.md), [ARCHITECTURE.md](ARCHITECTURE.md).
- Déploiement et production : [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md), [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md), [render.yaml](render.yaml).
- API et mobile : [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md), [eebc_mobile/README.md](eebc_mobile/README.md), [eebc_mobile/docs/PUBLIC_FEATURES.md](eebc_mobile/docs/PUBLIC_FEATURES.md).
- Audit Atlas Prime : [.skill/AGENTS.md](.skill/AGENTS.md), [.skill/.gemini/context/audit-checklist.md](.skill/.gemini/context/audit-checklist.md), [.skill/.codex/skills/atlas-prime/references/security-checklist.md](.skill/.codex/skills/atlas-prime/references/security-checklist.md), [.skill/.codex/skills/atlas-prime/templates/audit-report.md](.skill/.codex/skills/atlas-prime/templates/audit-report.md).

## Architecture
- Backend : Django 4.2, Python, DRF/JWT, Celery/Redis, WeasyPrint, Stripe, Hostinger SMTP, stockage Cloudinary conditionnel en production.
- Frontend web : templates Django, Bootstrap 5, HTMX et Alpine.js. Ne pas introduire React.
- Mobile : Flutter dans [eebc_mobile](eebc_mobile), avec Provider, GoRouter, Dio, JWT refresh sérialisé, cache local SharedPreferences.
- Configuration Django : [gestion_eebc/settings/base.py](gestion_eebc/settings/base.py), `dev.py`, `test.py`, `prod.py`. Les tests utilisent [gestion_eebc/settings/test.py](gestion_eebc/settings/test.py).
- Apps métier sous [apps](apps) : garder les responsabilités locales aux apps; éviter de déplacer du métier entre apps sans justification explicite.

## Commandes Utiles
- Installer le backend : `pip install -r requirements/dev.txt`.
- Lancer Django : `python manage.py runserver`.
- Tests backend : `pytest`, `pytest -m security`, `pytest --cov=apps`.
- Contrôle sécurité Django : `python manage.py check --deploy`.
- Qualité backend alignée CI : `flake8 apps --count --max-complexity=10 --max-line-length=127 --statistics`, `black --check apps gestion_eebc`, `isort --check-only apps gestion_eebc`.
- Audit sécurité CI : `bandit -r apps gestion_eebc --skip B101,B601,B607`, `safety check`, `pip-audit`, Semgrep via workflow.
- Mobile depuis [eebc_mobile](eebc_mobile) : `flutter pub get`, `flutter analyze`, `flutter test`, `flutter run -d android`.

## Conventions De Travail
- Respecter le système de rôles custom (`User.role` CSV, décorateurs `@role_required`, mixins associés) au lieu d'introduire le modèle Django `Permission` sans migration planifiée.
- Toute modification métier doit vérifier permissions, validations de formulaires, impacts admin, logs d'audit et tests existants.
- Les changements touchant paiements, reçus, imports, uploads, API, données membres ou communications doivent être traités comme sensibles.
- Les tests partagés utilisent [conftest.py](conftest.py) et [test_factories.py](test_factories.py); réutiliser les fixtures et factories existantes.
- En test, Celery est eager, l'email est en mémoire et le stockage média est temporaire; cela ne prouve pas le comportement Redis, SMTP, Cloudinary ou Render.
- Les fichiers Firebase mobiles (`google-services.json`, `GoogleService-Info.plist`) ne sont pas dans le dépôt et ne doivent pas être ajoutés.

## Audit
- Commencer par définir le périmètre, les données sensibles, les acteurs/roles et les chemins d'entrée (`urls.py`, vues, formulaires, serializers, templates, tasks, webhooks).
- Vérifier au minimum : contrôle d'accès, validation d'entrées, CSRF/XSS/IDOR/path traversal, secrets et logs, uploads, intégrations externes, migrations, performance des requêtes et couverture de tests.
- Pour la finance, vérifier Stripe signature/idempotence, création de transactions, reçus PDF/email, montants, devises, exports et journalisation.
- Pour les documents/imports/uploads, vérifier taille/type de fichier, visibilité par rôle, chemins de stockage, Cloudinary/local fallback et erreurs utilisateur.
- Pour l'API/mobile, vérifier JWT, refresh token, blacklist, rate limiting, endpoints publics et cohérence avec [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md).
- Livrer les audits avec constats en premier, classés par gravité, puis validations faites, risques résiduels et prochaines corrections recommandées.
