# DEPLOY — Production Deployment Guide

**Last Updated** : 2026-04-21  
**Target Platform** : Render  
**Status** : Production-Ready

---

## 📋 Pre-Deployment Checklist

- [ ] All tests passing (`pytest --cov=apps`)
- [ ] Code reviewed + merged to `main` branch
- [ ] Env vars prepared (no secrets in repo)
- [ ] Database backups enabled
- [ ] Email backend tested (Hostinger)
- [ ] Stripe webhook configured (production keys)
- [ ] SSL/TLS enforced (HTTPS only)
- [ ] Rate-limit middleware enabled
- [ ] Health check endpoint working
- [ ] Logging configured (structured JSON)
- [ ] Celery worker + Redis verified
- [ ] Rollback procedure documented

---

## 1. Environment Variables (Production)

### Required Vars

```bash
# Django
SECRET_KEY=your-secret-key-here-at-least-50-chars-do-not-reuse-from-dev
DEBUG=False
ALLOWED_HOSTS=gestion.eglise-ebc.org,www.gestion.eglise-ebc.org

# Database
DATABASE_URL=postgresql://user:password@host:5432/gestion_eebc

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
CSRF_TRUSTED_ORIGINS=https://gestion.eglise-ebc.org

# Email (Hostinger)
EMAIL_BACKEND=apps.core.infrastructure.hostinger_email_backend.HostingerEmailBackend
HOSTINGER_EMAIL_HOST_USER=noreply@eglise-ebc.org
HOSTINGER_EMAIL_HOST_PASSWORD=secure-app-password-from-hostinger
DEFAULT_FROM_EMAIL=noreply@eglise-ebc.org

# Stripe (Production Keys)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLIC_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_live_...

# Celery
CELERY_BROKER_URL=redis://redis-host:6379/0
CELERY_RESULT_BACKEND=redis://redis-host:6379/1

# Cache
CACHE_URL=redis://redis-host:6379/2

# Logging
LOG_LEVEL=INFO
SENTRY_DSN=https://key@sentry.io/project-id  # Optional error tracking
```

**Never commit `.env` or secrets to git.**

---

## 2. Database Migration

### Pre-Migration Backup

```bash
# On Render or local production DB
pg_dump gestion_eebc > backup_2026-04-21.sql
# Store in secure location (S3, encrypted backup)
```

### Run Migrations

```bash
# Render runs this automatically in the release phase:
# release: python manage.py migrate

# Or manually:
python manage.py migrate
```

### Verify

```bash
python manage.py migrate --check  # Safe, no changes
python manage.py showmigrations --list  # All green?
```

---

## 3. Deployment Process

### Option A: Render (Recommended)

#### Setup on Render

1. **Create Web Service**
   - Git repo: `https://github.com/beaudelaire1/gestion-eebc`
   - Branch: `main` (production)
   - Runtime: Python 3.10+
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn gestion_eebc.wsgi:application --bind 0.0.0.0:10000`

2. **Add Environment Variables** (Render Dashboard)
   - Copy all vars from "Required Vars" above
   - Use Render's encryption for secrets

3. **Setup Release Command** (Render Dashboard → Settings)
   ```bash
   python manage.py migrate
   ```

4. **Add PostgreSQL Database** (Render Dashboard)
   - Create new PostgreSQL instance
   - Copy `DATABASE_URL` to Web Service env vars

5. **Add Redis** (for Celery)
   - Create new Redis instance
   - Copy URL to `CELERY_BROKER_URL` and `CACHE_URL`

6. **Add Background Worker** (Render Dashboard → New Service)
   - Type: Background Worker
   - Git repo: same as above
   - Build command: `pip install -r requirements.txt`
   - Start command: `celery -A gestion_eebc worker -l info`
   - Env vars: copy from Web Service (must match)

#### Trigger Deploy

```bash
# Push to main (after develop tested)
git checkout main
git merge develop  # Or pull request
git push origin main

# Render auto-deploys on push to main
# Check Render Dashboard for build progress
```

#### Monitor Deploy

- Render Dashboard → Logs → Web Service
- Watch for: "Started gunicorn..." message
- Health check: `curl https://gestion.eglise-ebc.org/health/`

#### Rollback (if needed)

```bash
# Revert git commit
git revert HEAD
git push origin main

# Or: Render Dashboard → Deployments → Previous → Rollback
```

---

### Option B: Docker + VPS

#### Build Docker Image

```bash
# Create Dockerfile (already in repo)
docker build -t gestion-eebc:1.0 .

# Tag for registry
docker tag gestion-eebc:1.0 your-registry/gestion-eebc:1.0

# Push to registry
docker push your-registry/gestion-eebc:1.0
```

#### Deploy with Docker Compose

```bash
# On VPS
docker-compose -f docker-compose.yml up -d

# Watch logs
docker-compose logs -f web
```

---

## 4. Post-Deployment Validation

### Health Check

```bash
curl https://gestion.eglise-ebc.org/health/
# Expected response:
# {
#   "status": "ok",
#   "timestamp": "2026-04-21T03:00:00Z",
#   "db": "ok",
#   "celery": {"status": "ok", "workers": 1},
#   "cache": "ok"
# }
```

### Email Test

```bash
# Trigger a test email
python manage.py shell
>>> from apps.core.infrastructure.hostinger_email_backend import HostingerEmailService
>>> result = HostingerEmailService.test_connection()
>>> print(result)
# Check: {'success': True, ...}
```

### Stripe Webhook

1. Login to Stripe Dashboard
2. Webhook endpoints → Add endpoint
3. URL: `https://gestion.eglise-ebc.org/webhooks/stripe/`
4. Events: `checkout.session.completed`
5. Copy webhook secret to `STRIPE_WEBHOOK_SECRET`

### Database

```bash
# SSH to Render database terminal
render psql
\dt  # List tables
SELECT COUNT(*) FROM finance_onlinedonation;  # Verify data
```

### Celery Worker

```bash
# SSH to Render background worker logs
render logs --service=celery-worker

# Should show:
# celery@xxx ready. (worker ready to accept tasks)
```

---

## 5. Monitoring & Alerts

### Log Aggregation (Recommended)

Use **CloudFlare Analytics** or **DataDog**:

```bash
# Install DataDog agent
pip install datadog-agent

# Configure in settings/production.py
LOGGING = {
    'handlers': {
        'datadog': {...},  # Ship logs to DataDog
    }
}
```

### Key Metrics to Monitor

- **Error Rate** : HTTP 5xx responses
- **Email Failures** : EmailLog.status = 'failed'
- **Celery Queue Depth** : Tasks pending
- **DB Connection Pool** : Exhaustion warnings
- **Webhook Signature Failures** : Possible attack

### Alert Rules

| Metric | Threshold | Action |
|--------|-----------|--------|
| Error rate > 1% (5 min avg) | Page oncall engineer |
| Celery broker down | Auto-restart worker |
| Email send failure > 3x | Alert, check Hostinger quota |
| DB disk usage > 90% | Alert ops, plan upgrade |
| Webhook invalid signature | Alert security + log to AuditLog |

---

## 6. Backup & Disaster Recovery

### Database Backups

#### Render (Automatic)

Render automatically backs up PostgreSQL daily. To restore:

1. Render Dashboard → PostgreSQL → Backups
2. Select backup date
3. Click "Restore"
4. Wait for completion (~5 min)

#### Manual Backup

```bash
# On VPS
pg_dump gestion_eebc > backup_$(date +%Y-%m-%d).sql
gzip backup_*.sql

# Upload to S3
aws s3 cp backup_*.sql.gz s3://your-backup-bucket/
```

### Data Restoration

```bash
# If needed:
psql gestion_eebc < backup_2026-04-21.sql
```

### RTO / RPO

- **RTO** (Recovery Time Objective) : < 1 hour (restore backup)
- **RPO** (Recovery Point Objective) : < 1 day (daily backups)

---

## 7. Security Hardening

### SSL/TLS

- ✅ HTTPS enforced (Render auto-provisions Let's Encrypt)
- ✅ `SECURE_SSL_REDIRECT=True`
- ✅ HSTS header: `Strict-Transport-Security: max-age=31536000`

### Headers

```bash
# Django middleware adds:
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'
```

### Rate-Limiting

```bash
# Middleware active on:
- Login attempts (5 per min)
- Password reset (3 per hour)
- Exports (5 per min)
- Webhook endpoints (1000 per hour)
```

### Secrets Rotation

Schedule quarterly:
```bash
# 1. Generate new Stripe keys in dashboard
# 2. Update STRIPE_SECRET_KEY in Render env vars
# 3. Deploy
# 4. Revoke old keys in Stripe

# 5. Change Hostinger app-specific password
# 6. Update EMAIL_HOST_PASSWORD in Render
# 7. Deploy

# 8. Rotate Django SECRET_KEY (affects sessions)
# 9. All users forced to re-login
```

---

## 8. Troubleshooting

### Symptoms: Web service crashes immediately

```bash
# Check logs
render logs --service=web

# Common causes:
# - Missing env var (DEBUG, SECRET_KEY)
# - Database connection failed
# - Migration error

# Fix:
# 1. Add missing env var
# 2. Re-deploy
```

### Symptoms: Emails not sending

```bash
# Check logs
render logs --service=web | grep "email"

# Verify:
# 1. HOSTINGER credentials valid
# 2. Email quota not exceeded (Hostinger)
# 3. Celery worker running (logs)
# 4. EMAIL_BACKEND correct

# Test:
python manage.py test_hostinger_email
```

### Symptoms: Stripe webhook not received

```bash
# Check logs
render logs --service=web | grep "webhook"

# Verify:
# 1. Webhook URL correct: https://gestion.eglise-ebc.org/webhooks/stripe/
# 2. Webhook secret matches STRIPE_WEBHOOK_SECRET
# 3. Endpoint configured in Stripe Dashboard
# 4. Webhook is "active" in Stripe

# Test with Stripe CLI:
stripe listen --forward-to https://gestion.eglise-ebc.org/webhooks/stripe/
stripe trigger checkout.session.completed
```

### Symptoms: Celery tasks not running

```bash
# Check worker logs
render logs --service=celery-worker

# Verify:
# 1. Worker actually running (logs show "ready")
# 2. CELERY_BROKER_URL correct
# 3. Redis instance running + accessible

# Restart worker:
# Render Dashboard → Background Worker → Restart
```

---

## 9. Release Notes Template

When deploying, create release notes:

```markdown
## Release 2026-04-21

### Features
- ✅ Donation email flow fixed (customer_details.email extraction)

### Fixes
- ✅ EmailMessage → EmailMultiAlternatives (PDF attachment support)
- ✅ Backend hasattr check for alternatives

### Tests
- ✅ 10 comprehensive donation email tests

### Docs
- ✅ ARCHITECTURE.md (system design)
- ✅ SETUP.md (local dev guide)
- ✅ DEPLOY.md (this file)

### Quality Metrics
- Tests: 45/100 → 55/100 (↑ 10pts)
- Average: 72/100 (target: 95/100)

### Upgrade Path
- No breaking changes
- Database migrations: none
- Deployment time: ~5 min

### Rollback
If issues: `git revert <commit-hash>` + push to main
```

---

## 📞 Support

- **Render Support** : https://render.com/support
- **Stripe Support** : https://support.stripe.com
- **Hostinger Support** : https://hostinger.com/support
- **Django Docs** : https://docs.djangoproject.com

---

## 📚 Related

- `ARCHITECTURE.md` — System design
- `SETUP.md` — Local development
- `plan.md` — Quality scorecard
- `README.md` — Project overview

---

**Last Deployment** : 2026-04-21 (code freeze)  
**Next Review** : After Sprint 1 (all domains 95/100)
