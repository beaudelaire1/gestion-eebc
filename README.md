# EEBC — Gestion Église Évangélique Baptiste de Cayenne

Plateforme de gestion complète pour l'Église Évangélique Baptiste de Cayenne (Guyane française).

## Stack technique

| Composant | Technologie |
|---|---|
| Backend | Django 4.2, Python 3.11 |
| Frontend | HTMX, Alpine.js, Bootstrap 5 |
| Base de données | PostgreSQL (prod), SQLite (dev) |
| API REST | Django REST Framework, JWT |
| PDF | WeasyPrint |
| Paiements | Stripe |
| Email | Hostinger SMTP |
| Messagerie | Meta WhatsApp Cloud API |
| Tâches async | Celery + Redis |
| Hébergement | Render |
| Mobile | Flutter (iOS & Android) |

## Modules applicatifs (18 apps)

| App | Fonction |
|---|---|
| `accounts` | Authentification, rôles, 2FA |
| `api` | API REST mobile + web |
| `bibleclub` | Club biblique enfants |
| `campaigns` | Campagnes de collecte |
| `communication` | Emails, SMS, WhatsApp, annonces |
| `core` | Configuration, sites, audit, CMS |
| `dashboard` | Tableau de bord agrégé |
| `departments` | Départements et organisation |
| `events` | Événements et inscriptions |
| `finance` | Transactions, budgets, reçus fiscaux |
| `groups` | Groupes cellulaires |
| `imports` | Import/Export de données |
| `inventory` | Équipements et matériel |
| `members` | Membres, familles, visites |
| `public` | CMS public (pages, news) |
| `transport` | Transport et conducteurs |
| `worship` | Services de culte, planning |
| `young` | Ministère jeunesse |

## Démarrage rapide

```bash
# Cloner et créer l'environnement
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/Mac

# Installer les dépendances
pip install -r requirements/dev.txt

# Configurer l'environnement
cp .env.example .env
# Éditer .env avec vos clés

# Initialiser la base
python manage.py migrate
python manage.py createsuperuser

# Lancer le serveur
python manage.py runserver
```

## Commandes utiles

```bash
pytest                              # Tests
pytest --cov=apps                   # Tests + couverture
python manage.py check --deploy     # Vérification sécurité
python manage.py collectstatic      # Fichiers statiques
```

## Structure du projet

```
gestion_eebc/settings/   # Configuration Django (base/dev/prod/test)
apps/                    # 18 applications métier
templates/               # 293 templates HTML
static/                  # CSS, JS, images
.skill/                  # Méthodologie Atlas Prime (agents IA)
.plan/                   # Plans de travail en cours
.github/workflows/       # CI/CD (tests, qualité, déploiement)
docs/                    # Documentation détaillée
```

## Documentation

- [LIRE_DABORD.md](LIRE_DABORD.md) — Point d'entrée rapide
- [docs/GUIDE_UTILISATEUR.md](docs/GUIDE_UTILISATEUR.md) — Guide utilisateur
- [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) — Documentation API
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) — Guide de déploiement

## Méthodologie

Ce projet utilise le cadre **Atlas Prime** (`.skill/`) pour le pilotage IA avec un protocole en 7 phases : lecture stratégique → registre de vérité → arbitrage → exécution → contrôle → livraison.

## Licence

Projet privé — Église Évangélique Baptiste de Cayenne.
