# Design Document - Security Audit Fixes

## Overview

Ce document décrit l'architecture technique et les solutions de design pour les corrections de sécurité, le refactoring architectural et les améliorations UI/UX du projet Gestion EEBC. L'objectif est de transformer l'application en une solution enterprise-grade, sécurisée et maintenable.

## Architecture

### Architecture Globale

```
┌─────────────────────────────────────────────────────────────────┐
│                         PRESENTATION                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Templates  │  │    HTMX     │  │   Static (CSS/JS)       │  │
│  │  (Jinja2)   │  │  Partials   │  │   Toasts, Charts        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                          MIDDLEWARE                              │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ Session      │  │ Rate         │  │ Audit              │    │
│  │ Timeout      │  │ Limiting     │  │ Logging            │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                           VIEWS                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  @login_required + @role_required() + RoleRequiredMixin  │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Function   │  │   Class     │  │   API Views             │  │
│  │  Views      │  │   Views     │  │   (JSON)                │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                       SERVICE LAYER                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ accounts/   │  │ finance/    │  │ bibleclub/              │  │
│  │ services.py │  │ services.py │  │ services.py             │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                         MODELS                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   User      │  │  AuditLog   │  │   Domain Models         │  │
│  │   (RBAC)    │  │             │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      ASYNC TASKS                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Celery Workers                        │    │
│  │   OCR Processing │ Email Sending │ Backup │ Cleanup     │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Flux d'Authentification Sécurisé

```
┌──────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────┐
│  Login   │────▶│  Rate    │────▶│  Authenticate│────▶│  Check   │
│  Form    │     │  Limit   │     │              │     │  2FA     │
└──────────┘     └──────────┘     └──────────────┘     └──────────┘
                                         │                   │
                                         ▼                   ▼
                                  ┌──────────────┐    ┌──────────────┐
                                  │ must_change  │    │   Session    │
                                  │ _password?   │    │   Create     │
                                  └──────────────┘    └──────────────┘
                                         │                   │
                                         ▼                   ▼
                                  ┌──────────────┐    ┌──────────────┐
                                  │ Signed Token │    │  Audit Log   │
                                  │ Redirect     │    │  Entry       │
                                  └──────────────┘    └──────────────┘
```

## Components and Interfaces

### 1. Système de Permissions RBAC (`apps/core/permissions.py`)

```python
# Interface du décorateur role_required
def role_required(*roles: str, redirect_url: str = 'dashboard:home'):
    """
    Décorateur pour restreindre l'accès aux vues par rôle.
    
    Args:
        *roles: Liste des rôles autorisés
        redirect_url: URL de redirection si accès refusé
    
    Usage:
        @login_required
        @role_required('admin', 'finance')
        def my_view(request):
            ...
    """
    pass

# Interface du mixin RoleRequiredMixin
class RoleRequiredMixin:
    """
    Mixin pour les vues basées sur classes.
    
    Attributes:
        allowed_roles: tuple de rôles autorisés
        permission_denied_message: message d'erreur
    
    Usage:
        class MyView(RoleRequiredMixin, TemplateView):
            allowed_roles = ('admin', 'finance')
    """
    allowed_roles: tuple = ()
    permission_denied_message: str = "Accès non autorisé"

# Fonctions utilitaires
def has_role(user, *roles) -> bool:
    """Vérifie si l'utilisateur a l'un des rôles spécifiés."""
    pass

def get_user_permissions(user) -> dict:
    """Retourne les permissions de l'utilisateur basées sur son rôle."""
    pass
```

### 2. Service Layer Pattern

```python
# apps/accounts/services.py
class AuthenticationService:
    """Service d'authentification centralisé."""
    
    @staticmethod
    def authenticate_user(username: str, password: str, request) -> tuple[User | None, str]:
        """
        Authentifie un utilisateur avec rate limiting et logging.
        Returns: (user, error_message)
        """
        pass
    
    @staticmethod
    def generate_password_change_token(user: User) -> str:
        """Génère un token signé pour le changement de mot de passe."""
        pass
    
    @staticmethod
    def verify_password_change_token(token: str) -> User | None:
        """Vérifie et retourne l'utilisateur du token."""
        pass
    
    @staticmethod
    def record_login_attempt(user: User, success: bool, ip: str):
        """Enregistre une tentative de connexion."""
        pass

# apps/finance/services.py
class TransactionService:
    """Service de gestion des transactions."""
    
    @staticmethod
    def create_transaction(data: dict, user: User) -> FinancialTransaction:
        """Crée une transaction avec validation et audit."""
        pass
    
    @staticmethod
    def validate_transaction(transaction: FinancialTransaction, user: User) -> bool:
        """Valide une transaction."""
        pass
    
    @staticmethod
    def get_dashboard_stats(user: User) -> dict:
        """Retourne les statistiques du dashboard."""
        pass
```

### 3. Middleware de Sécurité

```python
# apps/core/middleware.py
class SessionTimeoutMiddleware:
    """
    Middleware de timeout de session.
    Déconnecte après SESSION_TIMEOUT_MINUTES d'inactivité.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout = getattr(settings, 'SESSION_TIMEOUT_MINUTES', 30)
        self.excluded_paths = getattr(settings, 'SESSION_TIMEOUT_EXCLUDED_PATHS', [])
    
    def __call__(self, request):
        # Vérifier le timeout
        # Mettre à jour last_activity
        pass

class RateLimitMiddleware:
    """
    Middleware de rate limiting.
    Limite les requêtes par IP/utilisateur.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.cache_prefix = 'ratelimit'
    
    def __call__(self, request):
        # Vérifier les limites
        # Retourner 429 si dépassé
        pass

class AuditMiddleware:
    """
    Middleware d'audit logging.
    Enregistre les actions sensibles.
    """
    pass
```

### 4. Modèle AuditLog

```python
# apps/core/models.py
class AuditLog(models.Model):
    """Journal d'audit des actions."""
    
    class Action(models.TextChoices):
        LOGIN = 'login', 'Connexion'
        LOGOUT = 'logout', 'Déconnexion'
        LOGIN_FAILED = 'login_failed', 'Échec connexion'
        CREATE = 'create', 'Création'
        UPDATE = 'update', 'Modification'
        DELETE = 'delete', 'Suppression'
        EXPORT = 'export', 'Export'
        ACCESS_DENIED = 'access_denied', 'Accès refusé'
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=Action.choices)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=50, blank=True)
    object_repr = models.CharField(max_length=200, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.CharField(max_length=500, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['model_name', '-timestamp']),
        ]
```

## Data Models

### Modèles de Sécurité

```python
# Extension du modèle User existant
class User(AbstractUser):
    # Champs existants...
    
    # Nouveaux champs pour rate limiting
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

# Modèle pour les tokens de changement de mot de passe
class PasswordChangeToken(models.Model):
    """Token sécurisé pour changement de mot de passe."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    def is_valid(self) -> bool:
        return not self.used and timezone.now() < self.expires_at
```

### Configuration des Rôles et Permissions

```python
# apps/core/permissions.py
ROLE_PERMISSIONS = {
    'admin': {
        'modules': ['*'],  # Accès total
        'actions': ['*'],
    },
    'secretariat': {
        'modules': ['members', 'accounts', 'events', 'groups'],
        'actions': ['view', 'create', 'update', 'export'],
    },
    'finance': {
        'modules': ['finance', 'campaigns'],
        'actions': ['view', 'create', 'update', 'export', 'validate'],
    },
    'responsable_club': {
        'modules': ['bibleclub'],
        'actions': ['view', 'create', 'update', 'export'],
    },
    'moniteur': {
        'modules': ['bibleclub'],
        'actions': ['view', 'update'],  # Sa classe uniquement
        'scope': 'own_class',
    },
    'responsable_groupe': {
        'modules': ['groups', 'worship'],
        'actions': ['view', 'update'],
        'scope': 'own_group',
    },
    'encadrant': {
        'modules': ['members'],
        'actions': ['view'],
        'scope': 'pastoral_data',
    },
    'membre': {
        'modules': ['members', 'events'],
        'actions': ['view'],
        'scope': 'public_only',
    },
}
```



## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Permission Enforcement

*For any* protected view and *for any* user, access is granted if and only if the user has at least one of the required roles for that view.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 2.3, 3.1, 3.2, 3.3, 3.4, 27.1, 27.2, 27.3, 28.1, 28.2**

### Property 2: Export Permission Verification

*For any* export operation and *for any* user, the export succeeds if and only if the user has the appropriate role for that data type (admin/secretariat for members, admin/responsable_club for children, admin/finance for transactions/budgets).

**Validates: Requirements 4.1, 4.2, 4.3, 4.4**

### Property 3: Audit Log Creation

*For any* sensitive action (login, logout, data modification, export, access denial), an AuditLog entry is created with the correct user, action type, and timestamp.

**Validates: Requirements 4.5, 5.4, 8.2, 8.3, 8.4**

### Property 4: Login Rate Limiting

*For any* IP address, after 5 failed login attempts within 1 minute, subsequent login attempts are blocked for 15 minutes.

**Validates: Requirements 5.2, 9.1**

### Property 5: Secure Password Change Flow

*For any* user requiring password change, the system uses a signed token (not plaintext password in session) and the token is valid only once and expires after a configured time.

**Validates: Requirements 5.1, 5.3**

### Property 6: Session Timeout

*For any* authenticated session, if no activity occurs for SESSION_TIMEOUT_MINUTES, the session is invalidated on the next request (excluding heartbeat URLs).

**Validates: Requirements 6.1, 6.4**

### Property 7: GPS Obfuscation

*For any* member displayed on the map, the coordinates returned are offset by 50-100 meters from the actual coordinates, unless the requesting user is an admin.

**Validates: Requirements 26.1, 26.2, 26.3**

### Property 8: CRUD Operations Integrity

*For any* CRUD operation on a model (create, update, delete), the operation succeeds if and only if the user has the required permissions, and the model state reflects the operation correctly.

**Validates: Requirements 10.1-10.5, 11.1-11.5, 12.1-12.4, 13.1-13.5, 14.1-14.5, 15.1-15.5**

### Property 9: Form Validation Consistency

*For any* form submission, server-side validation produces the same result as client-side validation for the same input data.

**Validates: Requirements 25.1, 25.2, 25.3**

### Property 10: Celery Task Execution

*For any* OCR upload, a Celery task is created and the task status is trackable until completion or failure.

**Validates: Requirements 17.1, 17.2, 17.3, 17.4**

## Error Handling

### Stratégie Globale

```python
# apps/core/exceptions.py
class PermissionDeniedError(Exception):
    """Accès refusé - rôle insuffisant."""
    def __init__(self, message="Vous n'avez pas les permissions nécessaires."):
        self.message = message
        super().__init__(self.message)

class RateLimitExceededError(Exception):
    """Limite de requêtes dépassée."""
    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        self.message = f"Trop de requêtes. Réessayez dans {retry_after} secondes."
        super().__init__(self.message)

class SessionExpiredError(Exception):
    """Session expirée."""
    pass

class InvalidTokenError(Exception):
    """Token invalide ou expiré."""
    pass
```

### Handlers d'Erreurs

```python
# gestion_eebc/views.py
def handler403(request, exception=None):
    """Page 403 personnalisée."""
    return render(request, 'errors/403.html', status=403)

def handler404(request, exception=None):
    """Page 404 personnalisée."""
    return render(request, 'errors/404.html', status=404)

def handler500(request):
    """Page 500 personnalisée avec logging."""
    import logging
    logger = logging.getLogger('django.request')
    logger.error('Internal Server Error', exc_info=True, extra={'request': request})
    return render(request, 'errors/500.html', status=500)
```

### Gestion des Erreurs dans les Services

```python
# Pattern de gestion d'erreurs dans les services
class ServiceResult:
    """Résultat d'une opération de service."""
    def __init__(self, success: bool, data=None, error: str = None):
        self.success = success
        self.data = data
        self.error = error
    
    @classmethod
    def ok(cls, data=None):
        return cls(success=True, data=data)
    
    @classmethod
    def fail(cls, error: str):
        return cls(success=False, error=error)
```

## Testing Strategy

### Framework et Outils

- **Framework de test**: pytest-django
- **Property-based testing**: hypothesis
- **Couverture**: pytest-cov (objectif: 70% minimum pour accounts et finance)
- **Mocking**: unittest.mock, pytest-mock
- **Tests E2E**: playwright (optionnel pour UI)

### Structure des Tests

```
tests/
├── conftest.py              # Fixtures partagées
├── factories.py             # Factory Boy pour génération de données
├── test_permissions.py      # Tests du système RBAC
├── test_audit.py            # Tests de l'audit logging
├── test_rate_limiting.py    # Tests du rate limiting
├── accounts/
│   ├── test_services.py     # Tests des services accounts
│   ├── test_views.py        # Tests des vues accounts
│   └── test_auth_flow.py    # Tests du flux d'authentification
├── finance/
│   ├── test_services.py     # Tests des services finance
│   ├── test_views.py        # Tests des vues finance
│   └── test_exports.py      # Tests des exports
└── core/
    ├── test_middleware.py   # Tests des middlewares
    └── test_models.py       # Tests des modèles
```

### Fixtures Pytest

```python
# tests/conftest.py
import pytest
from apps.accounts.models import User

@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username='admin',
        password='testpass123',
        role='admin'
    )

@pytest.fixture
def finance_user(db):
    return User.objects.create_user(
        username='finance',
        password='testpass123',
        role='finance'
    )

@pytest.fixture
def membre_user(db):
    return User.objects.create_user(
        username='membre',
        password='testpass123',
        role='membre'
    )

@pytest.fixture
def authenticated_client(client, admin_user):
    client.force_login(admin_user)
    return client
```

### Tests Property-Based avec Hypothesis

```python
# tests/test_permissions.py
from hypothesis import given, strategies as st
import pytest

ROLES = ['admin', 'secretariat', 'finance', 'responsable_club', 
         'moniteur', 'responsable_groupe', 'encadrant', 'membre']

@given(role=st.sampled_from(ROLES))
def test_role_required_decorator_blocks_unauthorized(role, client, db):
    """
    Property 1: Permission Enforcement
    Pour tout rôle non autorisé, l'accès est refusé.
    """
    # Créer un utilisateur avec ce rôle
    user = User.objects.create_user(username=f'test_{role}', role=role)
    client.force_login(user)
    
    # Tester l'accès à une vue finance (requiert admin ou finance)
    if role not in ['admin', 'finance']:
        response = client.get('/finance/dashboard/')
        assert response.status_code in [302, 403]

@given(attempts=st.integers(min_value=1, max_value=10))
def test_rate_limiting_blocks_after_threshold(attempts, client, db):
    """
    Property 4: Login Rate Limiting
    Après 5 tentatives échouées, le compte est bloqué.
    """
    for i in range(attempts):
        response = client.post('/accounts/login/', {
            'username': 'test',
            'password': 'wrong'
        })
    
    if attempts >= 5:
        # Vérifier que la 6ème tentative est bloquée
        response = client.post('/accounts/login/', {
            'username': 'test',
            'password': 'wrong'
        })
        assert response.status_code == 429 or 'bloqué' in response.content.decode()
```

### Tests Unitaires Prioritaires

```python
# tests/accounts/test_services.py
class TestAuthenticationService:
    def test_generate_password_change_token_is_unique(self, db, admin_user):
        """Le token généré est unique et signé."""
        token1 = AuthenticationService.generate_password_change_token(admin_user)
        token2 = AuthenticationService.generate_password_change_token(admin_user)
        assert token1 != token2
    
    def test_verify_token_returns_user(self, db, admin_user):
        """Un token valide retourne l'utilisateur."""
        token = AuthenticationService.generate_password_change_token(admin_user)
        user = AuthenticationService.verify_password_change_token(token)
        assert user == admin_user
    
    def test_expired_token_returns_none(self, db, admin_user):
        """Un token expiré retourne None."""
        # Créer un token expiré
        token = PasswordChangeToken.objects.create(
            user=admin_user,
            token='expired_token',
            expires_at=timezone.now() - timedelta(hours=1)
        )
        result = AuthenticationService.verify_password_change_token('expired_token')
        assert result is None

# tests/test_audit.py
class TestAuditLogging:
    def test_login_creates_audit_log(self, client, db, admin_user):
        """Property 3: Une connexion crée un AuditLog."""
        client.post('/accounts/login/', {
            'username': 'admin',
            'password': 'testpass123'
        })
        
        log = AuditLog.objects.filter(
            user=admin_user,
            action=AuditLog.Action.LOGIN
        ).first()
        assert log is not None
    
    def test_export_creates_audit_log(self, authenticated_client, db):
        """Property 3: Un export crée un AuditLog."""
        authenticated_client.get('/export/members/')
        
        log = AuditLog.objects.filter(
            action=AuditLog.Action.EXPORT
        ).first()
        assert log is not None
```

### Configuration CI/CD

```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements/dev.txt
      - name: Run tests with coverage
        run: |
          pytest --cov=apps --cov-report=xml --cov-fail-under=70
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Implementation Notes

### Ordre d'Implémentation Recommandé

1. **Phase 1 - Sécurité Critique** (Priorité Haute)
   - Système RBAC (`apps/core/permissions.py`)
   - Sécurisation des vues existantes (carte membres, finance, exports)
   - Correction du flux de login (token signé)
   - Middleware de session timeout

2. **Phase 2 - Infrastructure** (Priorité Haute)
   - Modèle AuditLog et signals
   - Rate limiting middleware
   - Service Layer (accounts, finance)

3. **Phase 3 - Modules CRUD** (Priorité Moyenne)
   - Complétion Inventory, Groups, Departments, Campaigns, Transport
   - Events CRUD complet

4. **Phase 4 - Fonctionnalités Avancées** (Priorité Moyenne)
   - OCR asynchrone avec Celery
   - Notifications email
   - Backup automatique

5. **Phase 5 - UI/UX** (Priorité Basse)
   - Système de Toasts
   - HTMX et Skeleton loaders
   - Dashboard Charts
   - Refonte CSS
   - Pages d'erreur personnalisées

6. **Phase 6 - Tests** (Continu)
   - Tests unitaires au fur et à mesure
   - Tests d'intégration
   - Property-based tests

### Dépendances Techniques

```
# requirements/base.txt (ajouts)
django-ratelimit>=4.0.0      # Rate limiting
hypothesis>=6.0.0            # Property-based testing
pytest-django>=4.5.0         # Tests Django
pytest-cov>=4.0.0            # Couverture de code
factory-boy>=3.2.0           # Factories pour tests
```

### Points d'Attention

1. **Migration de données**: Les modifications du modèle User nécessitent une migration
2. **Rétrocompatibilité**: Les décorateurs RBAC doivent être ajoutés progressivement
3. **Performance**: Le rate limiting utilise le cache Django (configurer Redis en prod)
4. **Sécurité**: Les tokens signés utilisent `django.core.signing`
