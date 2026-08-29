# 🚀 PLAN D'ACTION DÉTAILLÉ - CORRECTIONS CRUD

**Date**: 8 février 2026  
**Durée estimée**: 7 jours  
**Priority**: HAUTE

---

## PHASE 1: CORRECTIONS CRITIQUES (J1-J2)

### 1️⃣ COMMUNICATION: Créer `forms.py` MANQUANT

**Fichier**: `apps/communication/forms.py`

**Statut**: ❌ N'EXISTE PAS

**Actions:**

```python
# apps/communication/forms.py - À CRÉER

from django import forms
from django.utils import timezone
from .models import Announcement, Notification, EmailLog, SMSLog
from apps.core.forms import EnhancedForm

class AnnouncementForm(EnhancedForm):
    """Formulaire de création/édition d'annonces."""
    
    title = forms.CharField(
        max_length=200,
        label="Titre",
        widget=forms.TextInput(attrs={
            'placeholder': 'Titre de l\'annonce',
            'class': 'form-control'
        })
    )
    
    content = forms.CharField(
        label="Contenu",
        widget=forms.Textarea(attrs={
            'placeholder': 'Contenu de l\'annonce',
            'rows': 5,
            'class': 'form-control'
        })
    )
    
    importance = forms.ChoiceField(
        choices=Announcement.Importance.choices,
        label="Importance",
        initial=Announcement.Importance.NORMAL
    )
    
    display_start_date = forms.DateTimeField(
        required=False,
        label="Affichage à partir de",
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )
    
    display_end_date = forms.DateTimeField(
        required=False,
        label="Affichage jusqu'au",
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )
    
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        label="Active"
    )
    
    notify_all = forms.BooleanField(
        required=False,
        label="Notifier tous les membres"
    )
    
    class Meta:
        fields = ['title', 'content', 'importance', 'display_start_date', 
                  'display_end_date', 'is_active', 'notify_all']


class NotificationForm(EnhancedForm):
    """Formulaire pour notifications programmées."""
    
    recipient_type = forms.ChoiceField(
        choices=[
            ('all', 'Tous les membres'),
            ('role', 'Par rôle'),
            ('group', 'Par groupe'),
            ('department', 'Par département'),
            ('custom', 'Personnalisé'),
        ],
        label="Type de destinataires"
    )
    
    title = forms.CharField(max_length=200, label="Titre")
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}))
    
    schedule_time = forms.DateTimeField(
        required=False,
        label="Programmer pour",
        help_text="Laisser vide pour envoyer immédiatement"
    )


class AnnouncementScheduleForm(EnhancedForm):
    """Formulaire pour planifier les annonces."""
    
    announcement = forms.ModelChoiceField(
        queryset=Announcement.objects.all(),
        label="Annonce"
    )
    
    start_date = forms.DateField(label="Date de début")
    end_date = forms.DateField(label="Date de fin")
    
    send_notification = forms.BooleanField(
        required=False,
        label="Envoyer une notification"
    )


class EmailTemplateForm(EnhancedForm):
    """Formulaire pour gérer les templates d'email."""
    
    name = forms.CharField(max_length=100, label="Nom du template")
    subject = forms.CharField(max_length=200, label="Sujet")
    body = forms.CharField(widget=forms.Textarea, label="Corps du message")
    
    class Meta:
        fields = ['name', 'subject', 'body']
```

**Mise à jour vues**:

```python
# apps/communication/views.py - À MODIFIER

from .forms import AnnouncementForm, NotificationForm  # Ajouter

@login_required
@role_required('admin', 'secretariat', 'communication')
def announcement_create(request):
    """Créer une annonce avec formulaire."""
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.author = request.user
            announcement.save()
            
            if form.cleaned_data.get('notify_all'):
                # Créer notifications
                create_notifications_for_announcement(announcement)
            
            messages.success(request, 'Annonce créée avec succès.')
            return redirect('communication:announcements')
    else:
        form = AnnouncementForm()
    
    return render(request, 'communication/announcement_form.html', {'form': form})


@login_required
@role_required('admin', 'secretariat', 'communication')
def announcement_edit(request, pk):
    """Éditer une annonce."""
    announcement = get_object_or_404(Announcement, pk=pk)
    
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            announcement = form.save()
            messages.success(request, 'Annonce mise à jour.')
            return redirect('communication:announcements')
    else:
        form = AnnouncementForm(instance=announcement)
    
    return render(request, 'communication/announcement_form.html', 
                  {'form': form, 'announcement': announcement})
```

**Templates**:

```html
<!-- templates/communication/announcement_form.html - À CRÉER -->

{% extends "base.html" %}
{% load render_form %}

{% block title %}Annonce{% endblock %}

{% block content %}
<div class="container">
    <h1>{% if announcement %}Éditer{% else %}Créer{% endif %} une annonce</h1>
    
    <form method="post" class="card card-body">
        {% csrf_token %}
        {{ form|render_form }}
        
        <div class="btn-group">
            <button type="submit" class="btn btn-primary">
                {% if announcement %}Mettre à jour{% else %}Créer{% endif %}
            </button>
            <a href="{% url 'communication:announcements' %}" class="btn btn-secondary">
                Annuler
            </a>
        </div>
    </form>
</div>
{% endblock %}
```

---

### 2️⃣ FINANCE: Implémenter SOFT-DELETE pour transactions

**Fichier**: `apps/finance/models.py`

**Problème**: DELETE sans traçabilité (immuabilité requise)

**Actions:**

```python
# apps/finance/models.py - À MODIFIER

from django.db import models
from django.utils import timezone

class FinancialTransaction(models.Model):
    # ... champs existants ...
    
    # Ajouter soft-delete:
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="Supprimée",
        help_text="Marquée comme supprimée (soft-delete)"
    )
    
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Supprimée le",
        editable=False
    )
    
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_transactions',
        verbose_name="Supprimée par",
        editable=False
    )
    
    deletion_reason = models.TextField(
        blank=True,
        verbose_name="Raison de la suppression"
    )
    
    # Manager pour exclure les transactions supprimées par défaut
    objects = models.Manager()  # All objects including deleted
    
    class TransactionManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(is_deleted=False)
    
    active = TransactionManager()
    
    class Meta:
        # ... existant ...
        indexes = [
            models.Index(fields=['is_deleted', 'date']),
            models.Index(fields=['is_deleted', 'status']),
        ]
    
    def soft_delete(self, user, reason=""):
        """Soft-delete avec audit trail."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.deletion_reason = reason
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'deletion_reason'])
        
        # Ajouter à l'audit log
        from apps.core.models import AuditLog
        AuditLog.objects.create(
            action='delete',
            model_name='FinancialTransaction',
            object_id=self.id,
            user=user,
            details=f"Transaction supprimée: {reason}"
        )
    
    def restore(self, user):
        """Restaurer une transaction supprimée."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
        
        from apps.core.models import AuditLog
        AuditLog.objects.create(
            action='restore',
            model_name='FinancialTransaction',
            object_id=self.id,
            user=user,
            details="Transaction restaurée"
        )
```

**Mise à jour vues**:

```python
# apps/finance/views.py - À MODIFIER

@login_required
@role_required('admin', 'finance')
@require_http_methods(["POST"])
def transaction_delete(request, pk):
    """Soft-delete une transaction avec traçabilité."""
    transaction = get_object_or_404(FinancialTransaction.active, pk=pk)
    
    reason = request.POST.get('reason', '')
    
    try:
        transaction.soft_delete(user=request.user, reason=reason)
        messages.success(request, 'Transaction supprimée avec traçabilité.')
    except Exception as e:
        messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('finance:transaction_list')


@login_required
@role_required('admin', 'finance')
def transaction_list(request):
    """Liste les transactions (excluant les supprimées par défaut)."""
    # Utiliser le manager 'active' qui exclut les supprimées
    transactions = FinancialTransaction.active.all()
    
    # Option pour admin de voir les supprimées
    if request.GET.get('show_deleted') == '1':
        deleted = FinancialTransaction.objects.filter(is_deleted=True)
        # Afficher aussi les supprimées
    
    # ... rest du code ...
```

---

## PHASE 2: AMÉLIORATIONS UX (J3-J4)

### 3️⃣ IMPORTS: Validation avancée

**Fichier**: `apps/imports/services.py`

**Amélioration**: Validation détaillée par ligne

```python
# apps/imports/services.py - À AMÉLIORER

class ImportValidator:
    """Validateur avancé pour imports."""
    
    def __init__(self, rows, import_type):
        self.rows = rows
        self.import_type = import_type
        self.errors = []
        self.warnings = []
        self.valid_rows = []
    
    def validate_all(self):
        """Valider tous les rows."""
        for idx, row in enumerate(self.rows, start=2):  # Start at 2 (header is 1)
            errors = self._validate_row(row, idx)
            if errors:
                self.errors.extend(errors)
            else:
                self.valid_rows.append(row)
    
    def _validate_row(self, row, row_number):
        """Valider une ligne spécifique."""
        errors = []
        
        if self.import_type == 'members':
            errors.extend(self._validate_member_row(row, row_number))
        elif self.import_type == 'children':
            errors.extend(self._validate_child_row(row, row_number))
        
        return errors
    
    def _validate_member_row(self, row, row_number):
        """Validation spécifique pour membres."""
        errors = []
        
        # Vérifier champs obligatoires
        required = ['first_name', 'last_name', 'email']
        for field in required:
            if not row.get(field, '').strip():
                errors.append({
                    'row': row_number,
                    'field': field,
                    'error': f'{field} est obligatoire',
                    'value': row.get(field, '')
                })
        
        # Vérifier email unique
        if row.get('email'):
            if Member.objects.filter(email=row['email']).exists():
                errors.append({
                    'row': row_number,
                    'field': 'email',
                    'error': 'Email déjà existant',
                    'value': row['email'],
                    'severity': 'warning'
                })
        
        # Vérifier format date
        if row.get('birth_date'):
            try:
                datetime.strptime(row['birth_date'], '%d/%m/%Y')
            except ValueError:
                errors.append({
                    'row': row_number,
                    'field': 'birth_date',
                    'error': 'Format date invalide (JJ/MM/AAAA)',
                    'value': row['birth_date']
                })
        
        return errors
    
    def get_report(self):
        """Générer rapport de validation."""
        return {
            'total_rows': len(self.rows),
            'valid_rows': len(self.valid_rows),
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'errors': self.errors,
            'warnings': self.warnings,
            'can_proceed': len(self.errors) == 0
        }
```

**Vue d'import améliorée**:

```python
# apps/imports/views.py - À AMÉLIORER

@login_required
@role_required('admin', 'secretariat')
def import_create(request):
    """Créer un import avec preview et validation."""
    if request.method == 'POST':
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            import_log = form.save(commit=False)
            import_log.imported_by = request.user
            
            # Lire le fichier
            file = request.FILES['file']
            df = pd.read_excel(file)
            rows = df.to_dict('records')
            
            # Valider
            validator = ImportValidator(rows, import_log.import_type)
            validator.validate_all()
            report = validator.get_report()
            
            # Sauvegarder rapport
            import_log.validation_report = report
            import_log.total_rows = len(rows)
            import_log.save()
            
            # Rediriger vers preview
            return redirect('imports:preview', pk=import_log.pk)
    else:
        form = ImportForm()
    
    return render(request, 'imports/import_form.html', {'form': form})


def import_preview(request, pk):
    """Afficher preview avec erreurs avant import."""
    import_log = get_object_or_404(ImportLog, pk=pk)
    report = import_log.validation_report
    
    if report['error_count'] > 0:
        return render(request, 'imports/import_errors.html', {
            'import_log': import_log,
            'report': report,
            'can_proceed': False
        })
    
    return render(request, 'imports/import_preview.html', {
        'import_log': import_log,
        'report': report,
        'can_proceed': True
    })
```

---

### 4️⃣ CORE: Interface de configuration

**Fichier**: `apps/core/views.py` et `apps/core/urls.py`

**Ajouter vues d'administration:**

```python
# apps/core/views.py - À AJOUTER

from django.contrib.admin.views.decorators import staff_member_required
from .models import Site, SiteSettings
from .forms import SiteSettingsForm

@login_required
@staff_member_required
def site_admin_list(request):
    """Liste des sites pour administration."""
    sites = Site.objects.all()
    return render(request, 'core/site_admin_list.html', {'sites': sites})


@login_required
@staff_member_required
def site_admin_edit(request, pk):
    """Éditer configuration d'un site."""
    site = get_object_or_404(Site, pk=pk)
    
    if request.method == 'POST':
        form = SiteForm(request.POST, instance=site)
        if form.is_valid():
            form.save()
            messages.success(request, 'Site mis à jour.')
            return redirect('core:site_admin_list')
    else:
        form = SiteForm(instance=site)
    
    return render(request, 'core/site_admin_form.html', {'form': form, 'site': site})


@login_required
@staff_member_required
def settings_admin(request):
    """Gérer les paramètres globaux."""
    settings_obj = SiteSettings.get_settings()
    
    if request.method == 'POST':
        form = SiteSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Paramètres mis à jour.')
            return redirect('core:settings')
    else:
        form = SiteSettingsForm(instance=settings_obj)
    
    return render(request, 'core/settings_form.html', {'form': form})
```

**URLs**:

```python
# apps/core/urls.py - À AJOUTER

urlpatterns = [
    # ... existant ...
    path('admin/sites/', views.site_admin_list, name='site_admin_list'),
    path('admin/sites/<int:pk>/edit/', views.site_admin_edit, name='site_admin_edit'),
    path('admin/settings/', views.settings_admin, name='settings'),
]
```

---

## PHASE 3: TESTS & OPTIMISATION (J5-J7)

### 📝 Tests à écrire

```python
# tests/test_communication_crud.py - À CRÉER

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.communication.models import Announcement
from apps.communication.forms import AnnouncementForm

User = get_user_model()

class AnnouncementCRUDTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='pass123'
        )
        self.user.role = 'admin'
        self.user.save()
        
        self.client = Client()
        self.client.login(username='admin', password='pass123')
    
    def test_announcement_create(self):
        """Tester création d'annonce."""
        data = {
            'title': 'Test Annonce',
            'content': 'Contenu test',
            'importance': 'normal',
            'is_active': True
        }
        response = self.client.post('/communication/announcements/create/', data)
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertEqual(Announcement.objects.count(), 1)
    
    def test_announcement_form_validation(self):
        """Tester validation du formulaire."""
        form = AnnouncementForm(data={
            'title': '',  # Vide
            'content': 'Test'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)

# tests/test_finance_soft_delete.py - À CRÉER

class FinancialTransactionSoftDeleteTest(TestCase):
    def test_soft_delete(self):
        """Tester soft-delete avec traçabilité."""
        transaction = FinancialTransaction.objects.create(...)
        
        transaction.soft_delete(user=self.user, reason="Erreur")
        
        self.assertTrue(transaction.is_deleted)
        self.assertIsNotNone(transaction.deleted_at)
        self.assertEqual(FinancialTransaction.active.count(), 0)
        self.assertEqual(FinancialTransaction.objects.count(), 1)
```

---

## 📅 CALENDRIER D'EXÉCUTION

| Jour | Tâche | Durée | Responsable |
|---|---|---|---|
| **J1** | Communication forms.py | 4h | Dev 1 |
| **J1** | Finance soft-delete | 4h | Dev 2 |
| **J2** | Tests C+F | 3h | QA |
| **J2** | Correction bugs | 2h | Dev 1+2 |
| **J3** | Imports validation | 4h | Dev 1 |
| **J3** | Core settings UI | 4h | Dev 2 |
| **J4** | Templates & CSS | 4h | Dev 1 |
| **J4** | Tests avancés | 3h | QA |
| **J5-J6** | Optimisation perf | 8h | Dev 1+2 |
| **J7** | Déploiement staging | 2h | DevOps |

---

## ✅ CHECKLIST DE VALIDATION

- [ ] **Communication**: forms.py créé et testé
- [ ] **Communication**: vues utilisant les formulaires
- [ ] **Communication**: templates créés
- [ ] **Finance**: soft-delete implémenté
- [ ] **Finance**: tests passés
- [ ] **Imports**: validation améliorée
- [ ] **Imports**: preview fonctionnelle
- [ ] **Core**: UI settings accessible
- [ ] **All**: Tests unitaires > 80%
- [ ] **All**: Performance queries optimisée
- [ ] **All**: Documentation mise à jour

---

## 📊 ÉTAT PRÉ-DÉPLOIEMENT

```
✅ Accounts: 100% - Production Ready
✅ Members: 100% - Production Ready
✅ Events: 100% - Production Ready
✅ Finance: 90% - En correction
✅ Campaigns: 100% - Production Ready
✅ Transport: 100% - Production Ready
🟡 Imports: 75% - En amélioration
🟡 Communication: 85% - En correction
✅ bibleclub: 100% - Production Ready
✅ Groups: 100% - Production Ready
✅ Worship: 100% - Production Ready
✅ Departments: 100% - Production Ready
✅ Inventory: 100% - Production Ready
✅ Public: 95% - Prêt
✅ Core: 70% - En amélioration
⚪ Dashboard: N/A
✅ API: 100% - Production Ready

TOTAL: 85% CRUD Global → 92% après corrections
```

---

*Fin du plan d'action*
