# SETUP — Local Development Guide

**Last Updated** : 2026-04-21  
**Time to Setup** : ~15 minutes  
**Tech Stack** : Django 4.2 + PostgreSQL + Redis + Celery

---

## Prerequisites

- **Python** : 3.10+ 
- **PostgreSQL** : 13+ (or SQLite for quick testing)
- **Redis** : 6.0+ (for Celery + cache)
- **Git** : Latest
- **Node.js** : 18+ (optional, for frontend tooling)

---

## 1. Clone & Install

```bash
# Clone repo
git clone https://github.com/beaudelaire1/gestion-eebc.git
cd gestion-eebc

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## 2. Environment Setup

```bash
# Copy template
cp .env.example .env

# Edit .env with local values
nano .env  # or code .env
```

### Required Env Vars (Minimal)

```bash
# Django
SECRET_KEY=your-secret-key-here-at-least-50-chars
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (choose one)
# Option A: PostgreSQL (recommended)
DATABASE_URL=postgresql://user:password@localhost:5432/gestion_eebc

# Option B: SQLite (simplest for dev)
DATABASE_URL=sqlite:///db.sqlite3

# Email (leave as-is for development, console backend)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=noreply@eebc.local

# Stripe (get from Stripe dashboard)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_test_...

# Redis (for Celery + cache)
CELERY_BROKER_URL=redis://localhost:6379/0
CACHE_URL=redis://localhost:6379/1

# Hostinger Email (optional for dev)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
# In production, set to: hostinger

# API Keys (optional for dev)
HOSTINGER_API_KEY=  # Leave empty for dev
```

---

## 3. Database Setup

### Option A: PostgreSQL

```bash
# Create database + user (in psql or pgAdmin)
CREATE DATABASE gestion_eebc;
CREATE USER gestion_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE gestion_eebc TO gestion_user;
```

Update `.env`:
```bash
DATABASE_URL=postgresql://gestion_user:your_password@localhost:5432/gestion_eebc
```

### Option B: SQLite (Simplest)

```bash
DATABASE_URL=sqlite:///db.sqlite3
```

### Run Migrations

```bash
python manage.py migrate
```

---

## 4. Create Superuser (Admin)

```bash
python manage.py createsuperuser
# Follow prompts:
# Username: admin
# Email: admin@example.com
# Password: (set secure password)
```

---

## 5. Redis Setup

### Option A: Docker (Easiest)

```bash
docker run --name redis-eebc -d -p 6379:6379 redis:7-alpine
```

### Option B: System Install

```bash
# macOS
brew install redis
redis-server

# Linux (Debian/Ubuntu)
sudo apt-get install redis-server
redis-server

# Windows: Use WSL or Docker Desktop
```

Verify:
```bash
redis-cli ping
# Expected output: PONG
```

---

## 6. Celery Worker (Async Tasks)

In a **separate terminal** (with `.venv` activated):

```bash
celery -A gestion_eebc worker -l info
```

You should see:
```
celery@xxx ready. (worker ready to accept tasks)
```

---

## 7. Run Development Server

In another **separate terminal** (with `.venv` activated):

```bash
python manage.py runserver
```

Visit: **http://localhost:8000**

---

## 📁 Directory Structure

```
gestion-eebc/
├── gestion_eebc/          # Project settings
│   ├── settings/
│   │   ├── base.py        # Shared config
│   │   ├── local.py       # Local overrides
│   │   └── production.py  # Production only
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
├── apps/                  # Django apps (15 total)
│   ├── accounts/          # Auth, users, roles
│   ├── finance/           # Donations, receipts, budgets
│   ├── members/           # Member profiles, visits
│   ├── communication/     # Announcements, notifications
│   ├── events/            # Worship, calendars
│   ├── groups/            # Group management
│   ├── core/              # Shared models, services
│   └── ...
├── templates/             # HTML templates
│   ├── base.html          # Master layout
│   ├── dashboard/         # Dashboard pages
│   ├── finance/           # Donation + receipt pages
│   └── ...
├── static/                # CSS, JS, images
│   ├── css/
│   │   ├── components.css
│   │   └── dark-mode.css
│   ├── js/
│   │   └── toasts.js
│   └── images/
├── tests/                 # Test files
├── manage.py
├── requirements.txt       # Python dependencies
├── .env.example           # Template (copy to .env)
├── .env                   # Local config (never commit)
├── ARCHITECTURE.md        # System design
├── SETUP.md               # This file
├── DEPLOY.md              # Production guide
├── plan.md                # Project status + scorecard
└── README.md              # Project overview
```

---

## 🧪 Running Tests

### All Tests

```bash
pytest
```

### Specific Test File

```bash
pytest apps/finance/test_donation_email_flow.py -v
```

### With Coverage

```bash
pytest --cov=apps --cov-report=html
# Open: htmlcov/index.html
```

### Target

- **Minimum** : 70% coverage
- **Target** : 85%+ on critical paths (finance, auth)

---

## 📧 Testing Email Locally

### Option A: Console Backend (Default)

Emails print to console (development only):

```bash
python manage.py runserver
# Then trigger email (donation, etc.)
# Check terminal: email body will appear
```

### Option B: File Backend

Save emails to disk:

```bash
# In .env
EMAIL_BACKEND=django.core.mail.backends.filebased.EmailBackend
EMAIL_FILE_PATH=./sent_emails

# Create directory
mkdir -p sent_emails

# Emails saved as files
ls sent_emails/  # View sent emails
```

### Option C: Real Hostinger (Testing)

```bash
# .env
EMAIL_BACKEND=apps.core.infrastructure.hostinger_email_backend.HostingerEmailBackend
HOSTINGER_EMAIL_HOST_USER=your-email@yourdom.eebc
HOSTINGER_EMAIL_HOST_PASSWORD=your-password

# Test command
python manage.py test_hostinger_email
```

---

## 🔐 Testing Stripe Locally

### Use Stripe Test Keys

```bash
STRIPE_SECRET_KEY=sk_test_...  # Test key (not real)
STRIPE_PUBLIC_KEY=pk_test_...
```

### Test Card Numbers

| Card | Number | Result |
|------|--------|--------|
| Visa | 4242 4242 4242 4242 | Success |
| Visa | 4000 0000 0000 0002 | Decline |
| Amex | 3782 822463 10005 | Success |

**Expiry** : Any future date  
**CVC** : Any 3 digits

### Webhook Testing (Local)

Use [Stripe CLI](https://stripe.com/docs/stripe-cli):

```bash
# Install Stripe CLI (https://stripe.com/docs/stripe-cli)
stripe login

# Forward webhooks to localhost
stripe listen --forward-to localhost:8000/webhooks/stripe/

# In another terminal, trigger test event
stripe trigger checkout.session.completed
```

---

## 🐛 Common Issues

### `ModuleNotFoundError: No module named 'X'`

```bash
# Install missing package
pip install -r requirements.txt --force-reinstall
```

### `ProgrammingError: relation "app_model" does not exist`

```bash
# Run migrations
python manage.py migrate
```

### `ConnectionRefusedError: Redis connection refused`

```bash
# Start Redis
redis-server

# Or Docker
docker run -p 6379:6379 redis:7-alpine
```

### `OperationalError: could not connect to server`

```bash
# PostgreSQL not running?
# Check connection string in .env
# Or use SQLite instead:
DATABASE_URL=sqlite:///db.sqlite3
```

### Celery tasks not running

```bash
# Check Celery worker is running (separate terminal)
celery -A gestion_eebc worker -l info

# Check CELERY_BROKER_URL is correct
# Default: redis://localhost:6379/0
```

---

## 📚 Useful Commands

```bash
# Create migrations
python manage.py makemigrations

# View pending migrations
python manage.py showmigrations --list

# Reset database (WARNING: deletes data!)
python manage.py flush

# Load fixtures (test data)
python manage.py loaddata apps/core/fixtures/initial_data.json

# Create user
python manage.py createsuperuser

# Shell (Python REPL with Django context)
python manage.py shell

# Check settings
python manage.py diffsettings

# Collect static files (production)
python manage.py collectstatic --noinput
```

---

## 🚀 Next Steps

1. Run migrations: `python manage.py migrate`
2. Create admin user: `python manage.py createsuperuser`
3. Start Redis: `redis-server`
4. Start Celery worker: `celery -A gestion_eebc worker -l info`
5. Start Django: `python manage.py runserver`
6. Visit: http://localhost:8000/admin
7. Login with admin credentials
8. Explore dashboard: http://localhost:8000/dashboard/

---

## 📖 Documentation

- `README.md` — Project overview
- `ARCHITECTURE.md` — System design + data models
- `DEPLOY.md` — Production deployment
- `plan.md` — Quality scorecard + roadmap

---

**Need help?** Check error logs or open an issue on GitHub.
