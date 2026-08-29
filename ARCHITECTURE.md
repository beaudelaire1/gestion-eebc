# ARCHITECTURE — gestion-eebc

**Version** : 1.0 (2026-04-21)  
**Status** : Production-Ready  
**Last Update** : Post-email-fix

---

## 📐 SYSTEM DESIGN

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         GESTION-EEBC                            │
│            Django 4.2 + Bootstrap 5.3 + HTMX + Celery           │
└─────────────────────────────────────────────────────────────────┘

PUBLIC LAYER (No Auth Required)
├── Donation page (`/don/`) → Stripe checkout
├── Public announcements (if enabled)
└── Static pages (landing, about)

┌─────────────────────────────────────────────────────────────────┐
AUTHENTICATED LAYER (Login Required)
├── Member dashboard
├── Donation history (own)
├── Profile management
└── Member-specific data

┌─────────────────────────────────────────────────────────────────┐
ADMIN LAYER (Role-Based)
├── Admin (all permissions)
├── Secretary (members, events, communications)
├── Finance (transactions, budgets, receipts)
├── Club Leader (attendance, children data)
└── Group Leader (group-specific data)

┌─────────────────────────────────────────────────────────────────┐
BACKGROUND SERVICES
├── Celery (async tasks: emails, OCR, reports)
├── Email (SMTP Hostinger + async fallback)
├── PDF generation (WeasyPrint async queue)
└── Webhooks (Stripe, WhatsApp, SMS)
```

---

## 🏗️ CORE MODULES (15 apps)

### Primary Apps

#### 1. **finance**
Handles donation flow, receipts, budgets, transactions.

**Key Classes**
- `OnlineDonation` — Stripe session + receipt tracking
- `FinancialTransaction` — All monetary flows (normalized)
- `TaxReceipt` — PDF + email delivery tracking
- `Budget` / `BudgetCategory` — Departmental budgets

**Stripe Flow**
```
Stripe Checkout → Webhook (event: checkout.session.completed)
  ↓
stripe_service._handle_checkout_completed(session)
  ↓
Extract: amount, donor_email (from customer_details.email), type
  ↓
Create: OnlineDonation + FinancialTransaction
  ↓
_enqueue_donation_receipt_email(donation_id)
  ├─ Try: Celery async (send_donation_receipt_email_task)
  └─ Fallback: sync _send_donation_receipt() if broker down
  ↓
Generate PDF + Send via Hostinger SMTP
  ↓
Update: OnlineDonation.receipt_email_sent_at + EmailLog.status
```

**Key Files**
- `apps/finance/stripe_service.py` — Stripe orchestration
- `apps/finance/donation_views.py` — Public + admin views
- `apps/finance/tasks.py` — Celery tasks (with retry)
- `apps/finance/test_donation_email_flow.py` — Comprehensive tests (10 paths)

**Security**
- ✅ Webhook signature validation (Stripe)
- ✅ Idempotence (session_id dedup)
- ✅ Email extraction from correct field (customer_details.email)
- ✅ Permission checks on all admin views
- ✅ Rate-limit on exports (5 req/min)

---

#### 2. **accounts**
User authentication, roles, 2FA, password management.

**Key Classes**
- `User` — Extended Django User (role, 2FA, last_login)
- `TwoFactor` — TOTP seeds, backup codes
- `PasswordResetToken` — Secure temporary tokens

**Auth Flow**
```
Login → check_password() + rate_limit() + 2FA prompt
  ↓
Session + CSRF token set
  ↓
Per-view: @login_required or permission_required()
  ↓
Admin panel: Role-based (admin, secretary, finance, etc.)
```

**Key Files**
- `apps/accounts/views.py` — Login, profile, user CRUD
- `apps/accounts/two_factor_views.py` — 2FA setup/verify
- `apps/accounts/decorators.py` — Custom permission checks

---

#### 3. **communication**
Announcements, notifications, email logs, SMS/WhatsApp integration.

**Key Classes**
- `Announcement` — Public + internal posts
- `Notification` — In-app alerts
- `EmailLog` — Delivery tracking (sent, failed, attempts)
- `SMSLog` — SMS delivery history
- `WhatsAppLog` — WhatsApp webhook logs

**Email Pipeline**
```
Django messages (forms) → JavaScript toast system
  ↓
Bulk notifications → Celery queue → Hostinger SMTP
  ↓
Each email → EmailLog record (status, error_message, sent_at)
```

**Key Files**
- `apps/communication/views.py` — CRUD + email logs
- `apps/communication/models.py` — Announcement, Notification, Logs
- `static/js/toasts.js` — Single toast system (no duplication)

---

#### 4. **members**
Member profiles, visits, life events, emergency contacts.

**Key Classes**
- `Member` — Person + church role
- `LifeEvent` — Births, baptisms, deaths, etc.
- `VisitTracking` — Kanban board (to visit, visited, inactive)
- `EmergencyContact` — Safe reference data

**Features**
- ✅ Member map (Leaflet.js geolocation)
- ✅ Kanban board (Drag-drop visit status)
- ✅ Soft-delete (is_active flag)
- ✅ Member association for donation auto-linking

**Key Files**
- `apps/members/views.py` — Profile, map, kanban
- `apps/members/models.py` — Member + LifeEvent
- `templates/members/kanban_board.html` — Drag-drop UI

---

#### 5. **campaigns**
Fundraising campaigns, donor tracking, goal management.

**Key Classes**
- `Campaign` — Name, goal, deadline, type
- `Donation` (Campaign-linked) — Donations per campaign
- `DonationGoal` — Monthly/quarterly targets

**Features**
- Auto-link Stripe donations to campaigns (via metadata)
- Public campaign page (without sensitive donor data)
- Progress tracking

---

### Secondary Apps (Supporting)

| App | Purpose |
|-----|---------|
| **core** | Shared models (AuditLog, Site), services, email backend, decorators |
| **events** | Worship services, events, calendars, PDF run sheets |
| **groups** | Group management, leaders, attendance |
| **worship** | Sermons, worship schedules, PDFs |
| **transport** | Transport requests, driver allocation |
| **inventory** | Asset tracking, maintenance logs |
| **departments** | Org structure, responsibilities |
| **bibleclub** | Children programs, attendance, learning materials |
| **imports** | CSV import framework for bulk data |
| **api** | (Minimal) REST endpoints (if needed) |

---

## 📊 DATA MODEL (Key Relationships)

```
User
├── (1:1) Member (optional, user may be admin-only)
├── (1:N) OnlineDonation (as donor, via email/member_id)
├── (1:N) FinancialTransaction (as author/approver)
└── (1:N) AuditLog (all actions logged)

OnlineDonation
├── (1:1) FinancialTransaction
├── (M:1) Member (optional, auto-linked if authenticated)
├── (M:1) Campaign (optional, if fundraising)
└── (1:N) EmailLog (receipt delivery tracking)

FinancialTransaction
├── (M:1) FinanceCategory (income/expense classification)
├── (M:1) Member (optional, for tithe/personal donations)
├── (M:1) Site (church branch, if multi-site)
└── (1:1) TaxReceipt (if donation)

Member
├── (1:1) User (optional, auth login)
├── (M:1) Site (church location)
├── (1:N) LifeEvent
├── (1:N) VisitTracking
└── (1:N) OnlineDonation (if authenticated user)

Announcement
├── (M:1) Category
├── (M:1) Author (User)
└── (1:N) Notification (fan-out)

TaxReceipt
├── (1:1) OnlineDonation OR FinancialTransaction
├── (1:N) EmailLog (delivery attempts)
└── PDF file (WeasyPrint generated)
```

---

## 🔄 REQUEST-RESPONSE CYCLES (Key Flows)

### 1. Public Donation Flow
```
GET /don/
  ↓ Template: donation_page.html
  ↓ If authenticated: prefill name + email, show member banner
  ↓ If not: show optional name field
  ↓
POST → Create Stripe Checkout Session
  ↓ Metadata: donation_type, site_id, member_id (if auth), campaign_id
  ↓
Stripe Client (JS) → opens checkout modal
  ↓
User completes payment (Stripe side)
  ↓
Stripe POSTs: event:checkout.session.completed → /webhooks/stripe/
  ↓
Signature validation → safe
  ↓
stripe_service._handle_checkout_completed(session)
  ↓ Idempotence check (session_id exists?)
  ↓ If new: create OnlineDonation + FinancialTransaction
  ↓ Enqueue receipt email (async with fallback)
  ↓ Return success (transaction_id, reference)
  ↓
User redirected to success page (or JS modal closes)
```

### 2. Member Donation Flow (Authenticated)
```
GET /don/ (user logged in)
  ↓ DonationPageView.get_context_data()
  ↓ Pass: user_authenticated=True, user_email, user_full_name, user_member_id
  ↓
Template renders:
  - Green banner: "{{ user_full_name }}, votre don sera automatiquement lié…"
  - Email prefilled + hidden
  - Name required (for accounting)
  ↓
POST → Stripe Checkout (with member_id in metadata)
  ↓
Webhook processes: OnlineDonation.member_id = {id}
  ↓
Receipt sent to member email
  ↓
Finance team: can link donation → member profile → tax receipt
```

### 3. Email Receipt Flow
```
Webhook → _enqueue_donation_receipt_email(donation_id)
  ↓
Try:
  send_donation_receipt_email_task.delay(donation_id)  # Celery async
  ↓ Task calls: stripe_service._send_donation_receipt(donation)
Catch Exception:
  Fallback: _send_donation_receipt(donation)  # sync
  ↓
_send_donation_receipt():
  ├─ Check: donor_email exists + not already sent
  ├─ Generate: PDF (WeasyPrint)
  ├─ Create: EmailMessage → EmailMultiAlternatives
  ├─ Attach: PDF file
  ├─ Send: via HostingerEmailBackend (SMTP)
  ├─ Log: EmailLog.status = 'sent', sent_at = now()
  ├─ Update: OnlineDonation.receipt_email_sent_at = now()
  └─ Return: True (success)
```

### 4. Export (Data Download) Flow
```
GET /admin/export/members/excel/
  ↓
ExportPermissionMixin.dispatch():
  ├─ Check: user authenticated
  ├─ Check: has_export_permission() (role-based)
  ├─ Rate-limit: 5 req/min (decorator)
  └─ Log: AuditLog (action=EXPORT)
  ↓
BaseExportView.get():
  ├─ Query: Members (with filters)
  ├─ Generate: Excel (via ExportService)
  ├─ Set: Content-Type, Content-Disposition (download)
  └─ Return: HttpResponse (binary)
  ↓
AuditLog records: user_id, action, model, record_count, filters
```

---

## 🔐 SECURITY ARCHITECTURE

### Threat Model (Key Scenarios)

#### 1. Stripe Payment Fraud
**Risk** : Attacker sends fake webhook → create donation without payment
**Mitigation**
- ✅ Webhook signature validation (Stripe API key check)
- ✅ Stripe SDK verification: `event.get('request')` authenticated
- ✅ No email sent if payment_status != 'paid'

#### 2. Email Injection (Donation Receipt)
**Risk** : Attacker submits malicious email → SMTP injection
**Mitigation**
- ✅ Email extracted from Stripe (trusted source)
- ✅ Validated by EmailMessage (Django ORM, no raw SMTP)
- ✅ Donor name + email never interpolated into SMTP headers

#### 3. Unauthorized Export
**Risk** : Secretary downloads Finance data, or non-admin gets Users list
**Mitigation**
- ✅ `ExportPermissionMixin` checks role + export_type mapping
- ✅ Rate-limit: 5 exports/min per user
- ✅ AuditLog: every export recorded (user, type, record count, filters)
- ✅ No exports for non-authenticated users

#### 4. Member Data Leakage
**Risk** : Member map exposed publicly; visit tracking accessed by wrong user
**Mitigation**
- ✅ `/members/map/` requires login
- ✅ Member details require permission (own profile or staff)
- ✅ Soft-delete: is_active=False hides inactive members

#### 5. Privilege Escalation (Role)
**Risk** : User changes role in DB or cookie
**Mitigation**
- ✅ Role stored in DB User model, validated on every request
- ✅ Session token + CSRF for form submissions
- ✅ No role in JWT (or if JWT, signature validated)

---

### IAM (Identity & Access Management)

#### Roles

| Role | Permissions |
|------|-------------|
| **admin** | All (users, finance, members, events, communications) |
| **secretary** | Members, events, announcements, user lists (no deletions) |
| **finance** | Transactions, budgets, receipts, exports, reports |
| **club_leader** | Children attendance, materials, group messaging |
| **group_leader** | Group members, events, transportation |
| **member** | Own profile, donation history, announcements (public only) |
| **guest** | Public pages, donation form, public announcements (if enabled) |

#### Permission Checks

**Decorators**
```python
@login_required              # User authenticated
@require_permission('member')  # Role-based
@require_permission('finance', 'admin')  # Multiple roles (OR logic)
```

**View-level**
```python
class MembersExportView(ExportPermissionMixin, BaseExportView):
    export_type = 'members'  # ← Maps to EXPORT_PERMISSIONS
```

**Query-level (soft-delete)**
```python
Member.objects.filter(is_active=True)  # Never return deleted
```

---

### Secrets Management

**Environment Variables** (`.env`, never in repo)
```
STRIPE_SECRET_KEY
STRIPE_PUBLIC_KEY
STRIPE_WEBHOOK_SECRET
EMAIL_HOST_USER
EMAIL_HOST_PASSWORD
HOSTINGER_API_KEY
CELERY_BROKER_URL (Redis)
SECRET_KEY (Django)
DEBUG (False in prod)
```

**Rotation Strategy**
- DB backups encrypted at rest
- Email credentials: use app-specific passwords (Hostinger)
- Stripe keys: rotate quarterly, old keys revoked
- Redis: requires AUTH if exposed to network

---

## 📈 PERFORMANCE ARCHITECTURE

### Database Optimization

**Indexes** (Applied)
```python
# apps/communication/models.py
class EmailLog(models.Model):
    status = models.CharField(db_index=True)  # Filter by sent/failed
    user_read = models.BooleanField(db_index=True)

# apps/events/models.py
class GroupMeeting(models.Model):
    date = models.DateField(db_index=True)

# apps/transport/models.py
class TransportRequest(models.Model):
    date_time = models.DateTimeField(db_index=True)
```

**Query Optimization**
- ✅ select_related() for FK (User, Member)
- ✅ prefetch_related() for M2M (Groups, Roles)
- ✅ Pagination (25-50 items per page)
- ✅ Aggregation for stats (Count, Sum) instead of Python loops

### Caching

**Frontend (CSS + JS)**
```
static/css/components.css     — Centralized, minified
static/css/dark-mode.css      — Override variables
static/js/toasts.js           — Single source (no duplication)
```

**Backend**
- ✅ Session caching (Django default)
- ✅ Rate-limit cache (Redis, 1 min window)
- ✅ Email log cache (recent sent emails, 1 hour TTL)

### Async Tasks (Celery)

**Low-Priority** (can be async, fallback to sync if broker down)
- Email sending (donation receipt, notifications)
- PDF generation (run sheets, reports)
- OCR processing (receipt proofs)
- Bulk imports (CSV)

**High-Priority** (sync, immediate)
- Payment processing (webhook)
- Auth (login, password reset)
- Data validation (form submission)

---

## 🚀 DEPLOYMENT & OPERATIONS

### Infrastructure

**Stack**
- **Hosting** : Render (Django + PostgreSQL + Redis)
- **DNS** : CloudFlare
- **Email** : Hostinger SMTP (outbound)
- **Payment** : Stripe (PCI-DSS certified)
- **CDN** : Optional (CloudFlare)

**Scaling**
- Horizontal: Render auto-scales dynos (web + worker)
- Vertical: PostgreSQL upgraded as needed
- Cache: Redis shared across web + worker

### Health Checks

**Endpoint** : `GET /health/`
```json
{
  "status": "ok",
  "timestamp": "2026-04-21T02:58:00Z",
  "db": "ok",
  "celery": {
    "status": "ok",
    "workers": 1
  },
  "cache": "ok"
}
```

### Monitoring

**Logs (Structured JSON)**
```json
{
  "timestamp": "2026-04-21T02:58:00Z",
  "level": "INFO",
  "request_id": "uuid-xxxx",
  "user_id": 42,
  "action": "donation_receipt_sent",
  "donation_id": 123,
  "status": "success",
  "duration_ms": 1250
}
```

**Alerts**
- Celery broker down (fallback engaged)
- Email send failure (> 3 retries)
- DB connection error
- Webhook signature mismatch (possible attack)

---

## 📋 DEPLOYMENT CHECKLIST

- [ ] All env vars loaded (no secrets in code)
- [ ] Database migrations applied
- [ ] Celery worker running + monitored
- [ ] Redis cache available
- [ ] Email backend tested (`python manage.py test_hostinger_email`)
- [ ] Stripe webhook configured (production key + endpoint)
- [ ] Health check passing
- [ ] Logs flowing to monitoring (CloudFlare, DataDog, or similar)
- [ ] Rollback procedure documented + tested
- [ ] SSL/TLS enforced (HTTPS only)
- [ ] CSRF + CORS properly configured
- [ ] Rate-limit middleware active

---

## 🔄 DEVELOPMENT WORKFLOW

### Local Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Fill in local values
python manage.py migrate
python manage.py runserver
```

### Testing
```bash
pytest apps/finance/test_donation_email_flow.py -v
pytest --cov=apps --cov-report=html  # 70%+ target
```

### Database Changes
```bash
python manage.py makemigrations
python manage.py migrate
```

### Deployment
```bash
git push origin develop  # CI/CD runs tests
git push origin main     # Production merge (after develop tested)
```

---

## 📚 RELATED DOCUMENTS

- `plan.md` — Quality scorecard + iteration plan
- `SETUP.md` — Local development guide
- `DEPLOY.md` — Production deployment checklist
- `SECURITY.md` — Detailed threat model (WIP)

---

**Last Audit** : 2026-04-21 (post-email-fix)  
**Next Review** : After Sprint 1 completion (all domains 95/100)
