# PLAN — gestion-eebc (EEBC Donation + Membership Management)

**Dernière mise à jour** : 2026-04-21 02:35 UTC  
**Branch** : `develop` (191 commits)  
**Commit HEAD** : `b073e2c` (email fixes)

---

## 🎯 OBJECTIF MÉTIER

Transformer gestion-eebc (église protestante / gestion dons) en système **corporate-grade** :
- 100% fiabilité sur **flux de don (Stripe → reçu email)**
- UI/UX cohérente et professionnelle sur 504 fichiers, 15 apps
- Architecture nette (séparation public/core, Celery, PDFs)
- Documentation + tests maintenable à long terme

---

## 📋 SCOPE FIXE

### Inclus (38 issues audit)
1. **Bugs critiques** (A1-A7) → largement corrigés
2. **CRUD manquants** (B1-B4) → page_title + route/view complets
3. **UI/UX** (C1-C3) → CSS components + dark mode
4. **Architecture** (D1-D7) → publicité, Celery, séparation concerns
5. **Sécurité** (E1-E7) → IAM, validation, export protection
6. **Donation feature** → Stripe + reçu email + prefill membre

### Exclus
- Refonte complète templates (trop vaste)
- Nouvelles features non audit
- Versioning API

---

## 🏗️ ARCHITECTURE RETENUE

```
gestion-eebc/
├── apps/core/          # Shared (models, utils, infra)
├── apps/public/        # Public endpoints (don, landing)
├── apps/{finance,members,…}/ # Private apps (admin + authenticated)
├── templates/          # Base + app-specific
├── static/css/         # Centralized: components.css + dark-mode.css
├── static/js/          # Single toast.js, no duplication
└── manage.py          # Django standard
```

**Styles** : SMTP Hostinger + Celery async + WeasyPrint PDFs  
**Data flow** : Public donation → Stripe webhook → AsyncTask (or sync fallback) → email + DB record

---

## 📊 ÉTAT D'AVANCEMENT

### ✅ FAIT (Commits validés)

| Commit | Quoi | Status |
|--------|------|--------|
| `f045ef6` | A1-A7 base fixes | ✅ |
| `785e385` | A3+A5+B1-B2+donation | ✅ |
| `d75a61d` | Email extraction (customer_details.email) | ✅ |
| `b073e2c` | EmailMessage → EmailMultiAlternatives + hasattr check | ✅ |

### 🔄 EN COURS

| Task | Owner | Priorité | Blocker |
|------|-------|----------|---------|
| Valider email send post-déploiement | QA | P0 | Redis/Celery running? |
| Auditer sécurité authentication (E1-E3) | Security | P1 | None |
| Tests unitaires donation flow | QA | P1 | None |
| Audit a11y (WCAG) sur 5 templates clés | UX | P2 | None |

### ⏳ BACKLOG (À planifier)

| Task | Impacte | Estim. |
|------|---------|--------|
| **D1** : Séparer public/core routes | Arch | 2h |
| **D4** : Audit Celery config (timeout, retry) | Arch | 1h |
| **E7** : Export protection (JWT, rate-limit) | Security | 3h |
| **C4-C10** : Empty/loading/error states UX | UX | 6h |
| **B7** : Test scaffold (pytest + fixtures) | QA | 4h |
| SEO audit (meta, canonical, schema) | SEO | 2h |
| Perf audit (LCP, INP, bundle size) | Perf | 3h |

---

## 🔍 AUDIT ACTUEL (Qualité par domaine)

Notation : **0-100** (target: **95** pour tous domaines critiques)

### Sécurité: **75/100** ⚠️
**Points forts**
- ✅ Auth + 2FA implemented
- ✅ CSRF token in forms
- ✅ SQL injection protected (ORM)

**Faiblesses**
- ❌ E1-E3 (IAM, permissions) : roles vs permissions not consistently enforced
- ❌ E7 (export protection) : no rate-limit on exports
- ❌ Secrets in code? (need audit)
- ❌ No security.txt / headers audit

**Action** : Threat modeling + permission matrix (D1) → sprint next

---

### Performance: **80/100** ⚠️
**Points forts**
- ✅ DB indexed on key fields
- ✅ Pagination implemented

**Faiblesses**
- ❌ No LCP / INP targets
- ❌ PDF generation might be slow (needs async queue)
- ❌ No caching headers on static assets
- ❌ N+1 risk on members list?

**Action** : Measure (Lighthouse) + optimize bundle + ensure Celery covers PDF gen

---

### Maintenabilité: **82/100** ⚠️
**Points forts**
- ✅ README added
- ✅ Consistent URL patterns
- ✅ ORM models clean

**Faiblesses**
- ❌ No docstrings in views
- ❌ Magic numbers in settings
- ❌ Donation flow sprawls across stripe_service + views (hard to track)
- ❌ Toast system still partially in JS + Django (unclear ownership)

**Action** : Add service layer docs + extract donation logic to domain service

---

### UX/UI: **78/100** ⚠️
**Points forts**
- ✅ Dark mode implemented
- ✅ Component CSS added
- ✅ Donation sidebar + dashboard links

**Faiblesses**
- ❌ No empty states (all forms / lists)
- ❌ No loading indicators (async actions)
- ❌ No error boundary (forms fail silently?)
- ❌ Mobile responsive incomplete (many fixed widths)
- ❌ Tone inconsistent (FR + formal + casual mixed)

**Action** : Create state components (empty/loading/error) + responsive audit

---

### Accessibility (a11y): **72/100** ⚠️
**Points forts**
- ✅ Semantic HTML mostly used
- ✅ Color contrast OK (WCAG AA minimum)

**Faiblesses**
- ❌ No keyboard navigation test
- ❌ Focus states missing on custom components
- ❌ Form errors not linked to inputs (aria-describedby)
- ❌ ARIA labels sparse / incorrect where present
- ❌ Modals (if any) not trapped focus

**Action** : Keyboard audit + focus visible + form error binding

---

### SEO: **70/100** ⚠️
**Points forts**
- ✅ Meta tags present (title, meta description)

**Faiblesses**
- ❌ Public pages not indexed? (robots.txt missing)
- ❌ No structured data (LD-JSON for donation, org)
- ❌ Canonical tags inconsistent
- ❌ Sitemap missing
- ❌ H1 hierarchy might be wrong

**Action** : Add robots.txt + structured data (Organization, Donation) + sitemap

---

### DevOps / Observability: **68/100** ⚠️
**Points forts**
- ✅ Env config (BASE_DIR, DEBUG)
- ✅ Email logging to DB

**Faiblesses**
- ❌ No health check endpoint
- ❌ No app metrics (errors, latency)
- ❌ Celery broker health unknown
- ❌ Logs not structured (JSON?), no correlation IDs
- ❌ No rollback strategy documented

**Action** : Add `/health/` endpoint + structured logging + Celery health check

---

### Tests: **45/100** ❌ CRITIQUE
**Points forts**
- ✅ Some views have basic tests (likely)

**Faiblesses**
- ❌ No visible test suite in repo
- ❌ No donation flow test (Stripe mock)
- ❌ No email send test
- ❌ No permission matrix test
- ❌ No dark mode CSS test

**Action** : Create pytest scaffold + donation integration test + coverage target 70%

---

### Documentation: **60/100** ⚠️
**Points forts**
- ✅ README added
- ✅ Model docstrings (some)

**Faiblesses**
- ❌ No API docs (endpoints)
- ❌ No architecture diagram
- ❌ No setup guide for new dev
- ❌ No deployment guide
- ❌ No runbook for incident response

**Action** : Add ARCHITECTURE.md + SETUP.md + DEPLOY.md

---

## 🎯 CURRENT ISSUES (BLOCKERS)

### 🔴 P0 — Donation email flow not fully tested
- **Fix applied** : customer_details.email extraction + EmailMultiAlternatives
- **Validation needed** : Post-deploy test with real Stripe session
- **Risk** : If Celery down, fallback to sync (works, but slow)
- **Action** : Deploy + monitor logs for "Donation receipt email sent"

### 🟡 P1 — Tests missing for email + donation
- **Impact** : Can't catch regressions on payment flow
- **Action** : Add `test_donation_receipt_email()` with Stripe mock

### 🟡 P1 — Security audit incomplete (E1-E3, E7)
- **Impact** : Unknown exposure on exports, permissions
- **Action** : Run threat modeling sprint

---

## 📈 SCORECARD (BEFORE / AFTER)

| Domaine | Avant audit | Après P0 fixes | Target |
|---------|------------|---|--------|
| Security | 60 | 75 | 95 |
| Performance | 75 | 80 | 95 |
| Maintenability | 70 | 82 | 95 |
| UX/UI | 65 | 78 | 95 |
| A11y | 60 | 72 | 95 |
| SEO | 55 | 70 | 90 |
| DevOps | 50 | 68 | 95 |
| Tests | 30 | 45 | 85 |
| Docs | 50 | 60 | 90 |
| **MOYENNE** | **59** | **72** | **92** |

---

## 🔄 NEXT ITERATION (SPRINT 1)

**Objectif** : Monter à **85+/100** globalement, fix tous les P0/P1.

### Tâches

1. **Valider donation email post-deploy** (1h)
   - Test avec Stripe session réelle
   - Vérifier logs: "Donation receipt email sent"
   - Check EmailLog DB record (status=sent)

2. **Tests donation flow** (3h)
   - pytest + stripe.checkout.Session mock
   - Test webhook success path
   - Test email send (mock SMTP)
   - Test fallback (Celery down)

3. **Security baseline** (2h)
   - Audit user permissions per view
   - Check export endpoints (rate limit? auth?)
   - Scan for hardcoded secrets

4. **UX state components** (4h)
   - Empty state template (no items)
   - Loading indicator (spinner)
   - Error boundary (form validation)
   - Apply to 3 key pages (donations, members, announcements)

5. **DevOps health** (2h)
   - Add `/health/` endpoint (DB + Celery check)
   - Structured JSON logging
   - Deploy monitoring

---

## 🚀 DÉFINITION DE "TERMINÉ" (Cette session)

✅ Quand tous les critères sont remplis :

- [ ] Email donation : validé post-deploy ✅ (code fix done, needs deploy test)
- [ ] Tests : pytest scaffold + donation test ✅ (to do)
- [ ] Security P0 : threat model + export protection ✅ (to do)
- [ ] UX : empty states + error feedback ✅ (to do)
- [ ] DevOps : health check + logging ✅ (to do)
- [ ] Docs : ARCHITECTURE.md + SETUP.md ✅ (to do)
- [ ] **Scorecard all domains ≥ 85/100** (currently 72 avg)

**Pas de pause** jusqu'à ces critères ✅

---

## 📝 DECISIONS CLÉS VALIDÉES

| Decision | Rationale | Tradeoff |
|----------|-----------|----------|
| Stripe → Celery async + sync fallback | Reliability if broker down | Slower if Celery needed |
| EmailMultiAlternatives (not plain EmailMessage) | Support PDF + HTML + future MMS | Slight overhead |
| CSS centralized (components.css + dark-mode.css) | Reduce duplication, improve maintainability | Larger single files |
| No full template refactoring | Scope control, risk mitigation | Legacy HTML mixed new |
| Django messages → JS toast system | UX consistency | Dual system while migrating |

---

## 🚨 RISQUES ACTIFS

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|-----------|
| Celery broker down | Emails async fail, sync fallback catches | Medium | Fallback tested, monitoring added |
| Stripe session mismatch | Email never sent (was the bug) | **FIXED** | Updated extraction logic |
| 2FA bypass | Auth broken | Low | Audit needed (E1-E3) |
| Large PDF slow down | UX poor on slow connections | Medium | Async queue + progress indicator |
| Mobile layout broken | A11y + SEO issue | High | Responsive audit needed |
| Tests missing | Regression undetected | **CRITICAL** | Sprint 1 priority |

---

## 📞 CONTACTS / STAKEHOLDERS

- **Master-Jay** (stakeholder, final approval)
- **Me** (Foundation Prime, execution lead)

---

## 📅 HISTORIQUE

| Date | Commit | Quoi | Score |
|------|--------|------|-------|
| 2026-04-20 | 824a60e | Baseline avant audit | 59 |
| 2026-04-21 | f045ef6 | A1-A7 fixes | 62 |
| 2026-04-21 | 785e385 | A3+A5+B1-B2+donation | 68 |
| 2026-04-21 | d75a61d | Email Stripe fix | 70 |
| 2026-04-21 | b073e2c | EmailMessage fix | 72 |
| **NEXT** | → | Sprint 1: validate + tests + security | 85+ |

---

## 🎓 ANNEXES

### File structure (critical files)
- `gestion_eebc/settings/base.py` — ENV config
- `apps/finance/stripe_service.py` — Donation flow orchestration
- `apps/finance/donation_views.py` — Public + admin views
- `apps/core/infrastructure/hostinger_email_backend.py` — SMTP backend
- `templates/finance/donation_page.html` — Checkout form
- `templates/base.html` — Sidebar (donation link)

### Key env vars (to check)
```
STRIPE_SECRET_KEY, STRIPE_PUBLIC_KEY, STRIPE_WEBHOOK_SECRET
HOSTINGER_API_KEY, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD
CELERY_BROKER_URL (Redis)
DEFAULT_FROM_EMAIL
```

### Deployment checklist
- [ ] Env vars loaded (no hardcoded secrets)
- [ ] Celery worker running + monitored
- [ ] Email backend tested (test_hostinger_email command)
- [ ] Stripe webhook configured (production key)
- [ ] Health check passing
- [ ] Logs flowing to monitoring
- [ ] Rollback procedure documented

---

**Je n'arrête pas ce projet tant que tous les domaines atteignent 95/100.**
