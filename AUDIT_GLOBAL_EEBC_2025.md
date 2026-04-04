# AUDIT GLOBAL EEBC — Juin 2025

> Audit complet couvrant : Sécurité, SEO, Performance, Accessibilité, UI/UX, Infrastructure, Qualité du code.

---

## TABLEAU DE SYNTHÈSE

| Domaine          | Score   | Critiques | Élevés | Moyens | Faibles |
|------------------|---------|-----------|--------|--------|---------|
| **Sécurité**     | 🟡 65%  | 2         | 2      | 2      | 1       |
| **SEO**          | 🟡 55%  | 2         | 3      | 2      | 0       |
| **Performance**  | 🟢 70%  | 1         | 0      | 5      | 0       |
| **Accessibilité**| 🔴 40%  | 1         | 4      | 2      | 0       |
| **Infra/DevOps** | 🟢 75%  | 1         | 0      | 2      | 1       |
| **Qualité Code** | 🟡 50%  | 3         | 3      | 4      | 2       |

---

## 1. 🔒 SÉCURITÉ

### 🔴 CRITIQUE

| # | Problème | Fichier | Fix |
|---|----------|---------|-----|
| S1 | **Open Redirect** — `next` param non validé dans login | `apps/accounts/views.py` L82-83 | Utiliser `url_has_allowed_host_and_scheme()` |
| S2 | **Session cookies non sécurisés** — `SESSION_COOKIE_HTTPONLY` et `SESSION_COOKIE_SAMESITE` absents | `gestion_eebc/settings/base.py` | Ajouter `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE='Strict'` |

### 🟠 ÉLEVÉ

| # | Problème | Fichier | Fix |
|---|----------|---------|-----|
| S3 | `X_FRAME_OPTIONS` absent de base.py (uniquement dans prod.py) | `gestion_eebc/settings/base.py` | Déplacer `X_FRAME_OPTIONS = 'DENY'` dans base.py |
| S4 | `mark_safe()` sur contenu potentiellement dynamique | `apps/core/widgets.py` L112, `apps/core/apps.py` L24 | Échapper les entrées utilisateur avant `mark_safe` |

### 🟡 MOYEN

| # | Problème | Fichier | Fix |
|---|----------|---------|-----|
| S5 | CSP avec `'unsafe-inline'` dans SCRIPT_SRC — réduit protection XSS | `gestion_eebc/settings/base.py` L170 | Migrer vers nonce-based CSP |
| S6 | `STRIPE_WEBHOOK_SECRET` default vide sans validation prod | `gestion_eebc/settings/dev.py` L61 | Valider que le secret est présent en production |

### ✅ Points positifs sécurité
- Password validators (4/4 activés)
- Rate limiting + session timeout (middleware custom)
- Protection brute force (lockout après échecs)
- 2FA (TOTP + backup codes)
- Stripe webhook signature validée
- HSTS 1 an en prod, SECURE_CONTENT_TYPE_NOSNIFF, Referrer-Policy
- CSP implémenté avec defaults corrects

---

## 2. 🔍 SEO

### 🔴 CRITIQUE

| # | Problème | Fichier | Fix |
|---|----------|---------|-----|
| E1 | **Pas d'Open Graph / Twitter Cards** — partage social absent | `templates/public/base.html` | Ajouter blocs `og:title`, `og:description`, `og:image`, `twitter:card` |
| E2 | **Pas de `<link rel="canonical">`** — risque contenu dupliqué | `templates/public/base.html` | Ajouter `{% block canonical %}<link rel="canonical" href="...">{% endblock %}` |

### 🟠 ÉLEVÉ

| # | Problème | Fichier | Fix |
|---|----------|---------|-----|
| E3 | **Pas de JSON-LD / Schema.org** (Organization, Event, NewsArticle) | Tous templates publics | Ajouter `<script type="application/ld+json">` |
| E4 | **Meta descriptions manquantes** sur 7/12 pages publiques | `event_detail.html`, `home.html`, `events_list.html`, `contact.html`, `register.html`, `sites.html`, `map.html` | Ajouter blocs `{% block meta_description %}` |
| E5 | **Pas de breadcrumbs structurés** | Templates publics | Ajouter `BreadcrumbList` JSON-LD |

### 🟡 MOYEN

| # | Problème | Fix |
|---|----------|-----|
| E6 | Pas de `rel="noopener noreferrer"` systématique sur liens externes | Audit + correction de tous les `target="_blank"` |
| E7 | Pas de `hreflang` (si multi-langue envisagé) | Ajouter si pertinent |

### ✅ Points positifs SEO
- `<html lang="fr">` correct
- Sitemap.xml fonctionnel (4 sections : static, news, events, pages)
- Robots.txt bien configuré
- Structure sémantique (nav, main, footer, article, section)
- H1 présents sur toutes les pages
- Meta descriptions dynamiques sur `news_detail` et `page`
- Images avec `alt` descriptifs et dynamiques
- PWA setup (manifest.json, apple-touch-icon, service worker)

---

## 3. ⚡ PERFORMANCE

### 🔴 CRITIQUE

| # | Problème | Fichier | Fix |
|---|----------|---------|-----|
| P1 | **Index manquants sur FinancialTransaction** — `status`, `transaction_type`, `transaction_date`, `category` filtrés sans index | `apps/finance/models.py` | Ajouter `Meta.indexes` |

### 🟡 MOYEN

| # | Problème | Fichier | Fix |
|---|----------|---------|-----|
| P2 | N+1 sur dashboard — boucle 100 membres sans select_related | `apps/dashboard/views.py` L89-93 | Ajouter `.select_related('site')` |
| P3 | Scripts sans `defer` — bloquent le rendu HTML | `templates/base.html` (HTMX, Chart.js, Bootstrap) | Ajouter `defer` sur scripts non-critiques |
| P4 | Pas de cache sur statistiques dashboard | `apps/dashboard/views.py` L35-80 | Cacher résultats (5-15 min TTL) |
| P5 | Pas de `loading="lazy"` sur images | `templates/public/home.html` | Ajouter `loading="lazy"` sur images below-the-fold |
| P6 | Import Excel synchrone bloquant | `apps/imports/views.py` L76-87 | Utiliser Celery si disponible |

### ✅ Points positifs performance
- `select_related` / `prefetch_related` utilisés dans la plupart des vues
- WhiteNoise + CompressedManifestStaticFilesStorage en prod
- CDN pour Bootstrap, Chart.js, HTMX
- Redis cache configuré en prod (fallback LocMem)
- Pagination sur toutes les ListViews
- Indexes bien définis sur Member et Event (8+ chaque)
- Validation taille/type fichier sur imports (10MB max)
- Middleware léger, pas de bottleneck

---

## 4. ♿ ACCESSIBILITÉ

### 🔴 CRITIQUE

| # | Problème | Fichier | Fix |
|---|----------|---------|-----|
| A1 | **Pas de lien "Skip to content"** | `templates/public/base.html` | Ajouter `<a href="#main-content" class="visually-hidden-focusable">Aller au contenu</a>` |

### 🟠 ÉLEVÉ

| # | Problème | Fix |
|---|----------|-----|
| A2 | **ARIA labels manquants** sur navbar, formulaires | Ajouter `aria-label`, `aria-required`, `aria-invalid` |
| A3 | **Styles focus absents** — navigation clavier invisible | Ajouter `:focus-visible` dans CSS |
| A4 | **Pas de `srcset`** pour images responsive | Ajouter `srcset` + `sizes` sur toutes les images |
| A5 | **Erreurs de formulaire non détaillées** par champ | Afficher erreurs inline avec `aria-describedby` |

### 🟡 MOYEN

| # | Problème | Fix |
|---|----------|-----|
| A6 | Contraste couleur limite (`#6c757d` sur `#f8f9fa` ≈ 4.5:1) | Augmenter contraste text-secondary |
| A7 | Images manquent de contexte descriptif suffisant | Enrichir `alt` avec plus de détails |

### ✅ Points positifs accessibilité
- Bootstrap 5 avec composants accessibles par défaut
- Labels séparés des inputs (pas seulement placeholders)
- Viewport meta correct
- Structure sémantique (nav, main, footer, article)
- Grid responsive Bootstrap bien utilisé

---

## 5. 🏗️ INFRASTRUCTURE & DEVOPS

### 🔴 CRITIQUE

| # | Problème | Fix |
|---|----------|-----|
| D1 | **Aucune stratégie de backup** — PostgreSQL sur Render Free sans backup auto | Mettre en place pg_dump automatisé ou upgrade Render |

### 🟡 MOYEN

| # | Problème | Fix |
|---|----------|-----|
| D2 | Pas de `.env.example` documentant toutes les env vars requises | Créer `.env.example` avec toutes les variables |
| D3 | Dépendances PDF (WeasyPrint) via apt-get uniquement | Documenter pour autres plateformes |

### ✅ Points positifs infra
- Render.yaml bien configuré (health check, auto-deploy, PostgreSQL)
- CI/CD : pytest + flake8/black/isort + bandit + safety + django check
- Coverage collectée et envoyée à CodeCov
- Sentry intégré (conditionnel)
- Logging structuré avec formatters verbose
- Pages d'erreur personnalisées (403, 404, 500) avec logging
- Gunicorn correctement configuré

---

## 6. 📝 QUALITÉ DU CODE

### 🔴 CRITIQUE

| # | Problème | Fichier | Fix |
|---|----------|---------|-----|
| Q1 | **Couverture tests = 17.52%** (3,108 / 17,744 lignes) | Global | Objectif minimum : 50%, idéal : 80% |
| Q2 | **13 apps sur 18 sans aucun test** (accounts, core, bibleclub, campaigns, communication, dashboard, departments, events, groups, imports, inventory, public, transport) | — | Prioriser accounts, core, campaigns |
| Q3 | **`dashboard.home()` = 199 lignes** — fonction monolithique | `apps/dashboard/views.py` L9-208 | Extraire en sous-fonctions ou service |

### 🟠 ÉLEVÉ

| # | Problème | Fichier | Fix |
|---|----------|---------|-----|
| Q4 | `bibleclub.children_list()` = 99 lignes, `take_attendance()` = 110 lignes | `apps/bibleclub/views.py` | Refactoriser |
| Q5 | `finance.tax_receipt_create()` = 71 lignes, business logic dans view | `apps/finance/views.py` L283 | Déplacer logique dans service |
| Q6 | bibleclub/views.py contient 27 fonctions dans un seul fichier | `apps/bibleclub/views.py` | Séparer en modules |

### 🟡 MOYEN

| # | Problème | Fix |
|---|----------|-----|
| Q7 | DRY : patterns Q() search dupliqués entre apps | Créer mixin/helper réutilisable |
| Q8 | Imports lazy dans fonctions (views) au lieu du top | Reorganiser imports |
| Q9 | Type hints absents sur views, models, forms | Ajouter progressivement |
| Q10 | TODO Firebase non implémenté | `apps/communication/notification_service.py` L233 |

### ✅ Points positifs qualité
- Services bien structurés avec docstrings (accounts, finance, communication)
- Type hints sur services principaux
- Factories (factory_boy) en place
- Modèles avec docstrings
- Linting CI (flake8, black, isort)

---

## PLAN DE CORRECTION PRIORISÉ

### 🚨 Phase 1 — Urgent (bloquant production)

| # | Action | Effort |
|---|--------|--------|
| 1 | **S1** Fix open redirect (login view) | 5 min |
| 2 | **S2** Ajouter SESSION_COOKIE_HTTPONLY + SAMESITE | 5 min |
| 3 | **S3** X_FRAME_OPTIONS dans base.py | 2 min |
| 4 | **P1** Index FinancialTransaction | 10 min |
| 5 | **D1** Script backup PostgreSQL + doc | 30 min |

### 🔶 Phase 2 — Avant mise en prod stable

| # | Action | Effort |
|---|--------|--------|
| 6 | **E1+E2** Open Graph + Canonical URLs | 30 min |
| 7 | **A1** Skip navigation link | 5 min |
| 8 | **A2+A3** ARIA labels + focus styles | 1h |
| 9 | **Q1+Q2** Tests pour accounts, core, campaigns | 4h |
| 10 | **Q3** Refactoriser dashboard.home() | 1h |
| 11 | **S4** Audit mark_safe() usages | 30 min |
| 12 | **D2** Créer .env.example | 15 min |

### 🟢 Phase 3 — Amélioration continue

| # | Action | Effort |
|---|--------|--------|
| 13 | **E3** JSON-LD Schema.org | 2h |
| 14 | **E4** Meta descriptions manquantes | 30 min |
| 15 | **P2-P5** Optimisations performance | 2h |
| 16 | **Q4-Q6** Refactorisation bibleclub + finance | 3h |
| 17 | **Q7-Q9** DRY + type hints | 4h |
| 18 | **A4-A7** Accessibilité avancée | 2h |
| 19 | **S5** Migration CSP nonce-based | 2h |
| 20 | Monter coverage à 50%+ | 8h |

---

## MÉTRIQUES CLÉS

| Métrique | Actuel | Cible |
|----------|--------|-------|
| Couverture tests | 17.52% | 50%+ |
| Apps testées | 5/18 | 18/18 |
| Vulnérabilités critiques | 2 | 0 |
| Score Lighthouse estimé (SEO) | ~65 | 90+ |
| Score Lighthouse estimé (Accessibilité) | ~55 | 85+ |
| Score Lighthouse estimé (Performance) | ~70 | 85+ |

---

*Audit réalisé le 2025-06-01 — Projet EEBC sur branche `develop`*
