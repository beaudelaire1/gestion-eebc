# Plan de travail global — EEBC

Date de dernière mise à jour : 2026-06-08 (session 4)

## État du projet

| Domaine | Note /10 | Cible | Statut |
|---|:---:|:---:|---|
| Méthodologie (.skill/.plan) | 8 | 8 | ✅ Terminé |
| Architecture & Structure | 8 → 8.5 | 8 | ✅ render.yaml restructuré (Redis, SECRET_KEY partagé) |
| Sécurité | 9 → 9.5 | 9 | ✅ XSS sanitize (nh3), json_script charts, DJANGO_ENV guard |
| Tests & Couverture | 7.5 → 8.5 | 8 | ✅ 464 tests, 60% couverture |
| CI/CD & Déploiement | 8 → 8.5 | 8 | ✅ Actions v4/v5, health check, codecov v4 |
| Documentation | 7 | 7 | ✅ Stable |
| Frontend & UX | 7.5 | 7.5 | ✅ Stable |
| Application Mobile | 6 | — | ⏭️ Hors scope (ignoré par demande) |
| Performance | 8 | 8 | ✅ Stable |
| Maintenabilité | 8 → 8.5 | 8 | ✅ Bare except fixés, nh3 sanitizer, is_staff→rôles |
| **Moyenne (hors mobile)** | **7.9 → 8.6** | **7.7** | ✅ **Cible largement dépassée** |

## Décisions structurantes

1. Architecture Modular Monolith Django, pas de migration React.
2. HTMX + Alpine.js pour l'interactivité frontend.
3. Atlas Prime comme cadre méthodologique IA.
4. Render (free → starter) comme hébergeur principal.
5. Celery pour les tâches async (email, notifications).

## Corrections réalisées (2026-06-08 — session 4)

### Sécurité (C2, C3, C4, H2, M3)
- [x] XSS : `|safe` retiré de toast.html
- [x] XSS : `|safe` → `|sanitize` (nh3) sur 3 templates CMS (news_detail, event_detail, page)
- [x] Nouveau filtre template `sanitize_tags.py` avec nh3 (bleach replacement)
- [x] Chart data : `|safe` → `json_script` sur 3 templates (bibleclub, finance, groups)
- [x] `is_staff` → rôles spécifiques dans communication/signals.py (2 endroits)
- [x] `is_staff` → rôles spécifiques dans finance/signals.py
- [x] `is_staff` → `has_any_role('admin','secretariat','pasteur')` dans events/views.py (2 endroits)
- [x] DJANGO_ENV safety guard : RuntimeError si RENDER=true + DJANGO_ENV=dev

### Architecture (C1, H3)
- [x] render.yaml restructuré : Redis sous `services:` (was `services_redis:`)
- [x] SECRET_KEY partagé web→worker via `fromService` (was duplicate `generateValue`)
- [x] 3 services + 1 database sous structure YAML correcte

### Tests (M1)
- [x] 226 nouveaux tests (238 → 464) couvrant POST/CRUD + GET pour 12 apps
- [x] Couverture : 48% → **60%**
- [x] 3 fichiers de tests : test_post_crud.py, test_coverage_boost.py, test_coverage_extra.py

### Maintenabilité (H1)
- [x] 6 `except:` nues → `except Exception:` ou types spécifiques
- [x] nh3==0.3.4 ajouté aux dépendances

### CI/CD (L1)
- [x] GitHub Actions : checkout@v3→v4, setup-python@v4→v5
- [x] codecov-action@v3→v4, upload-artifact@v3→v4
- [x] Health check activé dans deploy.yml

## Corrections réalisées (2026-04-07 — session 3)

### Sécurité
- [x] HMAC X-Hub-Signature-256 sur le webhook WhatsApp
- [x] 6 vues communication/ : is_staff → _is_comm_admin() (rôles)
- [x] import_detail + import_status : @role_required ajouté
- [x] Bug critique Notification.objects.create : `recipient`→`user`, `link`→`action_url` (3 fichiers signals)

### Performance
- [x] Pagination (25/page) : finance, events, transport, worship, campaigns, groups, departments, communication
- [x] select_related('leader') : groups, departments
- [x] Indexes DB vérifiés (déjà en place)

### Tests
- [x] 47 nouveaux tests de vues (dashboard, members, events, finance, worship, communication, campaigns, groups, departments, transport, inventory, accounts)
- [x] Résultat : **236 tests, 48% couverture** (était 189 tests, 46%)

### Accessibilité
- [x] Attributs alt ajoutés sur 3 templates images

### Infrastructure
- [x] Celery worker + Redis ajoutés dans render.yaml
- [x] venv/ doublon supprimé (~200 MB récupérés)

### Maintenabilité
- [x] Logging (import logging + logger) dans les 18 views.py

## Corrections réalisées (2026-04-07 — session 2)

- [x] AGENTS.md : chemins corrigés (pyproject.toml → requirements.txt, config/ → gestion_eebc/)
- [x] dev.py : WhatsApp/Twilio tokens chargés depuis .env (plus hardcodés vide)
- [x] CORS prod : localhost retiré de la whitelist production
- [x] README.md créé
- [x] Plan global créé (.plan/plan.md)
- [x] 34 fichiers .md historiques archivés → docs/archives/
- [x] 10 nouveaux fichiers tests créés (accounts, communication, events, bibleclub, campaigns, groups, departments, inventory, transport, imports)
- [x] 12 échecs de tests corrigés → 189 tests passent, couverture 46%
- [x] CI flake8 : supprimé --exit-zero (build échoue sur vrais erreurs)

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
