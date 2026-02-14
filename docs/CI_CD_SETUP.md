"""
CONFIGURATION CI/CD GITHUB ACTIONS - GESTION EEBC
==================================================

Ce guide vous montre comment configurer et utiliser la CI/CD automatisée.

WORKFLOWS DISPONIBLES
====================

1. tests.yml - Tests, linting et sécurité
   - Run pytest avec couverture de code
   - Lint avec flake8, black, isort
   - Scan de sécurité avec bandit
   - Django security checks

2. deploy.yml - Déploiement automatique sur Render
   - Déclenché après tests réussis
   - Hook de déploiement Render
   - Health checks
   - Notifications Slack

3. code-quality.yml - Qualité de code avancée
   - Pylint analysis
   - Radon complexity checks
   - Dependency scanning
   - SAST avec Semgrep


CONFIGURATION INITIALE
====================

1. Variables d'environnement GitHub Secrets

Aller dans: Settings > Secrets and variables > Actions

Ajouter les secrets suivants:

Required:
  RENDER_DEPLOY_HOOK
    - Copier depuis Render: Settings > Deploy Hook
    - URL: https://api.render.com/deploy/srv-xxxxx

Optional:
  SLACK_WEBHOOK_URL
    - Créer un webhook Slack pour les notifications
    - URL: https://hooks.slack.com/services/...


2. Configuration du repository

Aller dans: Settings

Activer:
  - Allow GitHub Actions to create and approve pull requests
  - Require status checks to pass before merging


UTILISATION
===========

Automatique:
  - Chaque `git push` déclenche les tests
  - PR déclenchent les tests avant merge

Manuel:
  - Actions > Select workflow > Run workflow
  - Voir l'onglet "Actions" pour les logs


BRANCHES PROTÉGÉES
==================

Pour `main`:

1. Require a pull request before merging
2. Require status checks to pass
3. Require branches to be up to date before merging
4. Require code reviews before merging (recommandé: 2 reviews)
5. Dismiss stale pull request approvals

Cela garantit que:
  - Les tests passent avant le merge
  - Le code est revu avant la production
  - Les déploiements ne sont automatiques que sur main


LOGS ET DEBUGGING
================

Afficher les logs:
  - Actions > [Workflow name] > [Run]
  - Cliquer sur le job pour voir le détail

Debug locale:
  - act: https://github.com/nektos/act
  - Installer: brew install act
  - Tester: act -l (lister les workflows)
  - Runner: act (exécuter localement)


ÉTAPES DE CHAQUE WORKFLOW
=========================

tests.yml:
  1. Setup Python 3.10 et 3.11
  2. Install dependencies
  3. Lint (flake8, black, isort)
  4. Pytest avec coverage
  5. Bandit security check
  6. Django check --deploy
  7. Build Docker image (optionnel)

deploy.yml:
  1. Trigger RENDER_DEPLOY_HOOK
  2. Wait for deployment (30x10s = 5 min)
  3. Health check
  4. Send Slack notification

code-quality.yml:
  1. Pylint analysis
  2. Radon complexity chart
  3. Dependency checking
  4. Semgrep SAST


SÉCURITÉ DES WORKFLOWS
=====================

Recommendations:
  - Secrets: Utiliser GitHub Encrypted Secrets
  - Permissions: Minimale par défaut
  - Actions: Pinned à des versions spécifiques
  - Checkout: v3 minimum
  - Artifact: Pas de mots de passe dedans


TROUBLESHOOTING
===============

❌ Tests échouent en local mais passent en CI?
  - Vérifier la variable DJANGO_SETTINGS_MODULE
  - Vérifier les dépendances (pip install -r requirements/dev.txt)
  - Vérifier la base de données (pytest crée une BD en mémoire)

❌ Deploy ne se déclenche pas?
  - Vérifier que RENDER_DEPLOY_HOOK est défini
  - Vérifier que tests.yml passe
  - Lire les logs du workflow deploy

❌ Linting échoue?
  - black --diff apps gestion_eebc (voir les diffs)
  - black apps gestion_eebc (auto-format)
  - isort apps gestion_eebc (auto-fix imports)

❌ Coverage trop bas?
  - pytest --cov=apps --cov-report=html (générer rapport HTML)
  - Voir apps/htmlcov/index.html
  - Augmenter les tests pour les modules non couverts


MAINTENANCE
===========

Mettre à jour:
  - Python version si versions mineures sortent
  - Dependencies dans requirements/dev.txt
  - Actions versions (3 mois après release)
  - Semgrep rules (mensuellement)


CONTACTS ET RESSOURCES
======================

- GitHub Actions Docs: https://docs.github.com/actions
- Django Testing: https://docs.djangoproject.com/en/4.2/topics/testing/
- Pytest: https://docs.pytest.org/
- Render Deploy Hooks: https://render.com/docs/deploy-hooks

"""
