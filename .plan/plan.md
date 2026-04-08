# Plan de travail global — EEBC

Date de dernière mise à jour : 2026-04-08 (session 5)

## État du projet

| Domaine | Note /10 | Cible | Statut |
|---|:---:|:---:|---|
| Méthodologie (.skill/.plan) | 8 | 8 | ✅ Terminé |
| Architecture & Structure | 8.5 | 8 | ✅ Stable |
| Sécurité | 9.5 | 9 | ✅ Stable |
| Tests & Couverture | 8.5 | 8 | ✅ 464 tests, 60% couverture |
| CI/CD & Déploiement | 8.5 → 9 | 8 | ✅ Fix __init__.py guard Render |
| Documentation | 7 | 7 | ✅ Stable |
| Frontend & UX | 7.5 | 7.5 | ✅ Stable |
| Application Mobile | 6 | — | ⏭️ Hors scope |
| Performance | 8 | 8 | ✅ Stable |
| Maintenabilité | 8.5 | 8 | ✅ Stable |
| **Moyenne (hors mobile)** | **8.6** | **7.7** | ✅ **Cible largement dépassée** |

## Décisions structurantes

1. Architecture Modular Monolith Django, pas de migration React.
2. HTMX + Alpine.js pour l'interactivité frontend.
3. Atlas Prime comme cadre méthodologique IA.
4. Render (free → starter) comme hébergeur principal.
5. Celery pour les tâches async (email, notifications).

## Historique des sessions

### Session 5 — 2026-04-08
- **Fix déploiement Render** : `settings/__init__.py` levait `RuntimeError` même quand `DJANGO_SETTINGS_MODULE=gestion_eebc.settings.prod` car l'`__init__.py` est importé comme package intermédiaire. Fix : le guard ne se déclenche plus que quand `__init__.py` est le module settings réel (pas un import transitif).

### Session 4 — 2026-06-08
- Sécurité : XSS (`|safe` → `|sanitize` nh3), `json_script` charts, `is_staff` → rôles spécifiques
- Architecture : render.yaml restructuré (Redis, SECRET_KEY partagé)
- Tests : 238 → 464 tests, 48% → 60% couverture
- Maintenabilité : bare except fixés, nh3 ajouté
- CI/CD : GitHub Actions v4/v5, codecov v4, health check

### Session 3 — 2026-04-07
- Sécurité : HMAC webhook WhatsApp, is_staff → rôles communication, bug Notification.objects.create
- Performance : pagination 25/page, select_related
- Tests : 189 → 236 tests, 46% → 48% couverture
- Infrastructure : Celery worker + Redis dans render.yaml
- Maintenabilité : logging dans 18 views.py

### Session 2 — 2026-04-07
- AGENTS.md corrigé, dev.py tokens .env, CORS prod nettoyé
- README.md créé, plan.md créé, 34 .md archivés
- 10 fichiers tests créés, 189 tests passent, couverture 46%
- CI flake8 sans --exit-zero

## Chantiers restants

### Templates cassés identifiés (basse priorité)
- [ ] dashboard/partials/quick_stats.html : variable user absente du contexte
- [ ] finance/transaction_detail.html : .user.username sur membre sans utilisateur
- [ ] bibleclub views : référence à `bible_class.name` (champ inexistant sur BibleClass)
- [ ] inventory views : référence à `category.equipment_set` (related_name manquant)
- [ ] events/partials/upcoming_events.html : format date utilise specifier time sur date

### Déferred (impact faible)
- [ ] 123 f-string logging → lazy % formatting (M2 — négligeable perf Django)
- [ ] Application mobile Flutter (ignorée cette session)

## Bugs pré-existants identifiés (non bloquants)

- `BibleClass` model n'a pas de champ `name` mais les vues y font référence
- `inventory.Category` n'a pas de reverse relation `equipment_set` (les vues update/delete cassent)
- Template `upcoming_events.html` utilise `|date:"H:i"` sur un objet `date` (pas `datetime`)

## Risques ouverts

- Token WhatsApp Meta expire périodiquement (nécessite System User permanent)
- Free Tier Render limité (0.5 GB RAM) — surveiller cold starts
- Celery configuré dans render.yaml mais pas encore déployé
- 2 templates avec bugs de rendu (quick_stats, transaction_detail)
