"""
Module d'export et d'impression générique.

Ce module fournit des vues génériques pour :
- Export Excel de toutes les données
- Génération PDF avec WeasyPrint
"""

from django.views.generic import View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
import json

from .services import ExportService
from .pdf_service import PDFService
from .permissions import has_role


# =============================================================================
# EXPORT PERMISSION MIXIN
# =============================================================================

# Configuration des permissions par type d'export
EXPORT_PERMISSIONS = {
    # Membres: admin, secretariat
    'members': ('admin', 'secretariat'),
    'members_excel': ('admin', 'secretariat'),
    'members_print': ('admin', 'secretariat'),
    
    # Enfants du club biblique: admin, responsable_club
    'children': ('admin', 'responsable_club'),
    'children_excel': ('admin', 'responsable_club'),
    'children_print': ('admin', 'responsable_club'),
    'attendance': ('admin', 'responsable_club'),
    'attendance_excel': ('admin', 'responsable_club'),
    'attendance_print': ('admin', 'responsable_club'),
    
    # Finance (transactions, budgets): admin, finance
    'transactions': ('admin', 'finance'),
    'transactions_excel': ('admin', 'finance'),
    'budgets': ('admin', 'finance'),
    'budgets_excel': ('admin', 'finance'),
    'budgets_print': ('admin', 'finance'),
    'budget_detail': ('admin', 'finance'),
    'budget_detail_excel': ('admin', 'finance'),
    
    # Utilisateurs: admin uniquement
    'users': ('admin',),
    'users_excel': ('admin',),
    'users_print': ('admin',),
    
    # Autres exports avec permissions par défaut (admin, secretariat)
    'events': ('admin', 'secretariat'),
    'events_excel': ('admin', 'secretariat'),
    'events_print': ('admin', 'secretariat'),
    'groups': ('admin', 'secretariat', 'responsable_groupe'),
    'groups_excel': ('admin', 'secretariat', 'responsable_groupe'),
    'groups_print': ('admin', 'secretariat', 'responsable_groupe'),
    'group_members': ('admin', 'secretariat', 'responsable_groupe'),
    'departments': ('admin', 'secretariat'),
    'departments_excel': ('admin', 'secretariat'),
    'departments_print': ('admin', 'secretariat'),
    'drivers': ('admin', 'secretariat'),
    'drivers_excel': ('admin', 'secretariat'),
    'drivers_print': ('admin', 'secretariat'),
    'inventory': ('admin', 'secretariat'),
    'inventory_excel': ('admin', 'secretariat'),
    'inventory_print': ('admin', 'secretariat'),
    'worship': ('admin', 'responsable_groupe'),
    'worship_excel': ('admin', 'responsable_groupe'),
    'worship_print': ('admin', 'responsable_groupe'),
}


class ExportPermissionMixin:
    """
    Mixin pour contrôler les permissions d'export par type de données.
    
    Ce mixin vérifie que l'utilisateur a les permissions nécessaires pour
    exporter un type de données spécifique. Les permissions sont définies
    dans EXPORT_PERMISSIONS. Les exports sont loggés dans AuditLog.
    
    Attributes:
        export_type (str): Type d'export (ex: 'members', 'children', 'transactions')
        permission_denied_message (str): Message d'erreur personnalisé
        permission_denied_redirect (str): URL de redirection si accès refusé
    
    Usage:
        class MembersExportView(ExportPermissionMixin, BaseExportView):
            export_type = 'members'
            ...
    
    Notes:
        - Ce mixin doit être placé AVANT les autres mixins/vues dans l'héritage
        - Les superusers et admins ont toujours accès
        - Nécessite que l'utilisateur soit authentifié
        - Les exports sont loggés dans AuditLog (Requirement 4.5)
    
    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
    """
    export_type = None
    permission_denied_message = "Vous n'avez pas les permissions nécessaires pour effectuer cet export."
    permission_denied_redirect = 'dashboard:home'
    
    def get_export_allowed_roles(self):
        """
        Retourne les rôles autorisés pour ce type d'export.
        
        Returns:
            tuple: Tuple des rôles autorisés
        """
        if self.export_type and self.export_type in EXPORT_PERMISSIONS:
            return EXPORT_PERMISSIONS[self.export_type]
        # Par défaut, seuls les admins peuvent exporter
        return ('admin',)
    
    def has_export_permission(self):
        """
        Vérifie si l'utilisateur a les permissions pour cet export.
        
        Returns:
            bool: True si l'utilisateur a les permissions requises
        """
        allowed_roles = self.get_export_allowed_roles()
        return has_role(self.request.user, *allowed_roles)
    
    def log_export(self, success=True, record_count=0):
        """
        Logger l'export dans AuditLog.
        
        Args:
            success: True si l'export a réussi
            record_count: Nombre d'enregistrements exportés
        
        Requirements: 4.5
        """
        from apps.core.models import AuditLog
        
        AuditLog.log_from_request(
            request=self.request,
            action=AuditLog.Action.EXPORT,
            model_name=self.export_type or 'unknown',
            extra_data={
                'export_type': self.export_type,
                'export_format': getattr(self, 'export_format', 'excel'),
                'record_count': record_count,
                'success': success,
                'filters': dict(self.request.GET) if self.request.GET else {}
            }
        )
    
    def dispatch(self, request, *args, **kwargs):
        """
        Vérifie les permissions avant de traiter la requête d'export.
        """
        # Vérifier que l'utilisateur est authentifié
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Vérifier les permissions d'export
        if not self.has_export_permission():
            # Logger la tentative d'export refusée
            from apps.core.models import AuditLog
            AuditLog.log_from_request(
                request=request,
                action=AuditLog.Action.ACCESS_DENIED,
                model_name=self.export_type or 'unknown',
                extra_data={
                    'export_type': self.export_type,
                    'required_roles': list(self.get_export_allowed_roles()),
                    'user_role': getattr(request.user, 'role', 'unknown')
                }
            )
            return self.handle_no_permission()
        
        return super().dispatch(request, *args, **kwargs)
    
    def handle_no_permission(self):
        """
        Gère le cas où l'utilisateur n'a pas les permissions d'export.
        """
        if self.request.user.is_authenticated:
            messages.error(self.request, self.permission_denied_message)
            return redirect(self.permission_denied_redirect)
        
        # Si non authentifié, rediriger vers login
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(self.request.get_full_path())


class BaseExportView(LoginRequiredMixin, View):
    """Vue de base pour les exports Excel."""
    
    model = None
    export_title = "Export"
    export_filename_prefix = "export"
    export_format = 'excel'
    
    def get_queryset(self):
        """Retourne le queryset à exporter."""
        return self.model.objects.all()
    
    def get_headers(self):
        """Retourne les en-têtes des colonnes."""
        raise NotImplementedError
    
    def get_row_data(self, obj):
        """Retourne les données d'une ligne."""
        raise NotImplementedError

    def get_export_data(self):
        """Prépare les données pour l'export."""
        data = []
        for obj in self.get_queryset():
            row = self.get_row_data(obj)
            if isinstance(row, dict):
                data.append(row)
            else:
                data.append(dict(zip(self.get_headers(), row)))
        return data
    
    def get_metadata(self):
        """Retourne les métadonnées de l'export."""
        return {
            'Utilisateur': self.request.user.get_full_name() or self.request.user.username,
            'Date': timezone.now().strftime('%d/%m/%Y %H:%M'),
        }
    
    def get(self, request, *args, **kwargs):
        """Génère et retourne le fichier Excel."""
        data = self.get_export_data()
        headers = self.get_headers()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.export_filename_prefix}_{timestamp}.xlsx"
        
        # Logger l'export si le mixin ExportPermissionMixin est présent
        if hasattr(self, 'log_export'):
            self.log_export(success=True, record_count=len(data))
        
        return ExportService.export_to_excel(
            data=data,
            headers=headers,
            title=self.export_title,
            filename=filename,
            metadata=self.get_metadata()
        )


class BasePDFView(LoginRequiredMixin, View):
    """Vue de base pour la génération de PDF avec WeasyPrint."""
    
    template_name = None
    pdf_title = "Document"
    pdf_filename_prefix = "document"
    export_format = 'pdf'
    
    def get_queryset(self):
        """Retourne le queryset à imprimer."""
        raise NotImplementedError
    
    def get_context_data(self):
        """Retourne le contexte pour le template."""
        return {
            'print_title': self.pdf_title,
            'print_date': timezone.now(),
            'user': self.request.user,
            'object_list': self.get_queryset(),
        }
    
    def get_filename(self):
        """Génère le nom du fichier PDF."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{self.pdf_filename_prefix}_{timestamp}.pdf"
    
    def get(self, request, *args, **kwargs):
        """Génère et retourne le PDF."""
        context = self.get_context_data()
        
        # Logger l'export si le mixin ExportPermissionMixin est présent
        if hasattr(self, 'log_export'):
            record_count = context.get('object_list', [])
            if hasattr(record_count, 'count'):
                record_count = record_count.count()
            elif hasattr(record_count, '__len__'):
                record_count = len(record_count)
            else:
                record_count = 0
            self.log_export(success=True, record_count=record_count)
        
        return PDFService.generate_pdf(
            template_name=self.template_name,
            context=context,
            filename=self.get_filename(),
            request=request
        )


# Alias pour compatibilité
class BasePrintView(BasePDFView):
    """Alias pour BasePDFView (compatibilité)."""
    pass


# =============================================================================
# EXPORTS BIBLECLUB (Enfants)
# =============================================================================

class ChildrenExportView(ExportPermissionMixin, BaseExportView):
    """Export des enfants du club biblique.
    
    Permissions: admin, responsable_club
    Requirements: 4.2
    """
    
    export_type = 'children'
    export_title = "Liste des Enfants - Club Biblique"
    export_filename_prefix = "enfants_club_biblique"
    
    def get_queryset(self):
        from apps.bibleclub.models import Child
        queryset = Child.objects.select_related('bible_class', 'bible_class__age_group')
        
        # Filtres optionnels
        if self.request.GET.get('active_only') == '1':
            queryset = queryset.filter(is_active=True)
        if self.request.GET.get('class_id'):
            queryset = queryset.filter(bible_class_id=self.request.GET.get('class_id'))
        if self.request.GET.get('needs_transport') == '1':
            queryset = queryset.filter(needs_transport=True)
        
        return queryset.order_by('last_name', 'first_name')
    
    def get_headers(self):
        return [
            'Nom', 'Prénom', 'Date de naissance', 'Âge', 'Genre',
            'Classe', 'Père', 'Tél. Père', 'Mère', 'Tél. Mère',
            'Transport', 'Allergies', 'Actif'
        ]
    
    def get_row_data(self, child):
        return {
            'Nom': child.last_name,
            'Prénom': child.first_name,
            'Date de naissance': child.date_of_birth.strftime('%d/%m/%Y') if child.date_of_birth else '',
            'Âge': child.age,
            'Genre': 'M' if child.gender == 'M' else 'F',
            'Classe': str(child.bible_class) if child.bible_class else '',
            'Père': child.father_name,
            'Tél. Père': child.father_phone,
            'Mère': child.mother_name,
            'Tél. Mère': child.mother_phone,
            'Transport': 'Oui' if child.needs_transport else 'Non',
            'Allergies': child.allergies or '-',
            'Actif': 'Oui' if child.is_active else 'Non'
        }


class ChildrenPrintView(ExportPermissionMixin, BasePDFView):
    """Impression PDF de la liste des enfants.
    
    Permissions: admin, responsable_club
    Requirements: 4.2
    """
    
    export_type = 'children'
    template_name = 'bibleclub/print/children_list.html'
    pdf_title = "Liste des Enfants - Club Biblique"
    pdf_filename_prefix = "enfants_club_biblique"
    
    def get_queryset(self):
        from apps.bibleclub.models import Child
        queryset = Child.objects.select_related('bible_class', 'bible_class__age_group')
        
        if self.request.GET.get('active_only') == '1':
            queryset = queryset.filter(is_active=True)
        if self.request.GET.get('class_id'):
            queryset = queryset.filter(bible_class_id=self.request.GET.get('class_id'))
        
        return queryset.order_by('last_name', 'first_name')
    
    def get_context_data(self):
        context = super().get_context_data()
        from apps.bibleclub.models import BibleClass
        context['classes'] = BibleClass.objects.filter(is_active=True)
        context['total_children'] = context['object_list'].count()
        context['active_children'] = context['object_list'].filter(is_active=True).count()
        return context


# =============================================================================
# EXPORTS MEMBRES
# =============================================================================

class MembersExportView(ExportPermissionMixin, BaseExportView):
    """Export des membres de l'église.
    
    Permissions: admin, secretariat
    Requirements: 4.1
    """
    
    export_type = 'members'
    export_title = "Liste des Membres"
    export_filename_prefix = "membres"
    
    def get_queryset(self):
        from apps.members.models import Member
        queryset = Member.objects.select_related('site', 'family')
        
        # Filtres optionnels
        if self.request.GET.get('status'):
            queryset = queryset.filter(status=self.request.GET.get('status'))
        if self.request.GET.get('site_id'):
            queryset = queryset.filter(site_id=self.request.GET.get('site_id'))
        if self.request.GET.get('baptized') == '1':
            queryset = queryset.filter(is_baptized=True)
        
        return queryset.order_by('last_name', 'first_name')
    
    def get_headers(self):
        return [
            'ID Membre', 'Nom', 'Prénom', 'Date de naissance', 'Genre',
            'Email', 'Téléphone', 'Ville', 'Statut', 'Baptisé(e)',
            'Date d\'arrivée', 'Site'
        ]
    
    def get_row_data(self, member):
        return {
            'ID Membre': member.member_id,
            'Nom': member.last_name,
            'Prénom': member.first_name,
            'Date de naissance': member.date_of_birth.strftime('%d/%m/%Y') if member.date_of_birth else '',
            'Genre': member.gender or '',
            'Email': member.email,
            'Téléphone': member.phone,
            'Ville': member.city,
            'Statut': member.get_status_display(),
            'Baptisé(e)': 'Oui' if member.is_baptized else 'Non',
            'Date d\'arrivée': member.date_joined.strftime('%d/%m/%Y') if member.date_joined else '',
            'Site': str(member.site) if member.site else ''
        }


class MembersPrintView(ExportPermissionMixin, BasePDFView):
    """Impression PDF de la liste des membres.
    
    Permissions: admin, secretariat
    Requirements: 4.1
    """
    
    export_type = 'members'
    template_name = 'members/print/members_list.html'
    pdf_title = "Liste des Membres"
    pdf_filename_prefix = "membres"
    
    def get_queryset(self):
        from apps.members.models import Member
        queryset = Member.objects.select_related('site', 'family')
        
        if self.request.GET.get('status'):
            queryset = queryset.filter(status=self.request.GET.get('status'))
        if self.request.GET.get('site_id'):
            queryset = queryset.filter(site_id=self.request.GET.get('site_id'))
        
        return queryset.order_by('last_name', 'first_name')
    
    def get_context_data(self):
        context = super().get_context_data()
        context['total_members'] = context['object_list'].count()
        context['active_members'] = context['object_list'].filter(status='actif').count()
        context['baptized_members'] = context['object_list'].filter(is_baptized=True).count()
        return context


# =============================================================================
# EXPORTS FINANCE (Budgets, Transactions)
# =============================================================================

class BudgetsExportView(ExportPermissionMixin, BaseExportView):
    """Export des budgets.
    
    Permissions: admin, finance
    Requirements: 4.4
    """
    
    export_type = 'budgets'
    export_title = "Liste des Budgets"
    export_filename_prefix = "budgets"
    
    def get_queryset(self):
        from apps.finance.models import Budget
        queryset = Budget.objects.select_related('group', 'department', 'created_by')
        
        if self.request.GET.get('year'):
            queryset = queryset.filter(year=self.request.GET.get('year'))
        if self.request.GET.get('status'):
            queryset = queryset.filter(status=self.request.GET.get('status'))
        
        return queryset.order_by('-year', 'name')
    
    def get_headers(self):
        return [
            'Nom', 'Année', 'Entité', 'Montant demandé', 'Montant approuvé',
            'Montant dépensé', 'Restant', 'Utilisation %', 'Statut', 'Créé par'
        ]
    
    def get_row_data(self, budget):
        return {
            'Nom': budget.name,
            'Année': budget.year,
            'Entité': str(budget.entity) if budget.entity else '',
            'Montant demandé': f"{budget.total_requested:.2f} €",
            'Montant approuvé': f"{budget.total_approved:.2f} €",
            'Montant dépensé': f"{budget.spent_amount:.2f} €",
            'Restant': f"{budget.remaining_amount:.2f} €",
            'Utilisation %': f"{budget.utilization_percentage:.1f}%",
            'Statut': budget.get_status_display(),
            'Créé par': budget.created_by.get_full_name() if budget.created_by else ''
        }


class BudgetDetailExportView(ExportPermissionMixin, BaseExportView):
    """Export détaillé d'un budget avec ses lignes.
    
    Permissions: admin, finance
    Requirements: 4.4
    """
    
    export_type = 'budget_detail'
    export_filename_prefix = "budget_detail"
    
    def get_budget(self):
        from apps.finance.models import Budget
        return get_object_or_404(Budget, pk=self.kwargs['pk'])
    
    def get_queryset(self):
        budget = self.get_budget()
        return budget.items.select_related('category').order_by('priority', 'category__name')
    
    def get_headers(self):
        return [
            'Catégorie', 'Description', 'Priorité', 'Montant demandé',
            'Montant approuvé', 'Montant dépensé', 'Restant', 'Statut'
        ]
    
    def get_row_data(self, item):
        return {
            'Catégorie': str(item.category),
            'Description': item.description[:100] + '...' if len(item.description) > 100 else item.description,
            'Priorité': item.priority,
            'Montant demandé': f"{item.requested_amount:.2f} €",
            'Montant approuvé': f"{item.approved_amount:.2f} €",
            'Montant dépensé': f"{item.spent_amount:.2f} €",
            'Restant': f"{item.remaining_amount:.2f} €",
            'Statut': item.get_approval_status_display()
        }
    
    def get(self, request, *args, **kwargs):
        budget = self.get_budget()
        self.export_title = f"Budget {budget.year} - {budget.entity}"
        return super().get(request, *args, **kwargs)


class TransactionsExportView(ExportPermissionMixin, BaseExportView):
    """Export des transactions financières.
    
    Permissions: admin, finance
    Requirements: 4.3
    """
    
    export_type = 'transactions'
    export_title = "Transactions Financières"
    export_filename_prefix = "transactions"
    
    def get_queryset(self):
        from apps.finance.models import FinancialTransaction
        queryset = FinancialTransaction.objects.select_related(
            'category', 'member', 'recorded_by', 'site'
        )
        
        # Filtres par date
        if self.request.GET.get('date_from'):
            queryset = queryset.filter(transaction_date__gte=self.request.GET.get('date_from'))
        if self.request.GET.get('date_to'):
            queryset = queryset.filter(transaction_date__lte=self.request.GET.get('date_to'))
        
        # Autres filtres
        if self.request.GET.get('type'):
            queryset = queryset.filter(transaction_type=self.request.GET.get('type'))
        if self.request.GET.get('status'):
            queryset = queryset.filter(status=self.request.GET.get('status'))
        
        return queryset.order_by('-transaction_date', '-created_at')
    
    def get_headers(self):
        return [
            'Référence', 'Date', 'Type', 'Montant', 'Méthode',
            'Catégorie', 'Membre', 'Description', 'Statut'
        ]
    
    def get_row_data(self, tx):
        return {
            'Référence': tx.reference,
            'Date': tx.transaction_date.strftime('%d/%m/%Y'),
            'Type': tx.get_transaction_type_display(),
            'Montant': f"{tx.amount:.2f} €",
            'Méthode': tx.get_payment_method_display(),
            'Catégorie': str(tx.category) if tx.category else '',
            'Membre': str(tx.member) if tx.member else '',
            'Description': tx.description[:50] + '...' if len(tx.description) > 50 else tx.description,
            'Statut': tx.get_status_display()
        }


class BudgetsPrintView(ExportPermissionMixin, BasePDFView):
    """Impression PDF de la liste des budgets.
    
    Permissions: admin, finance
    Requirements: 4.4
    """
    
    export_type = 'budgets'
    template_name = 'finance/print/budgets_list.html'
    pdf_title = "Liste des Budgets"
    pdf_filename_prefix = "budgets"
    
    def get_queryset(self):
        from apps.finance.models import Budget
        queryset = Budget.objects.select_related('group', 'department', 'created_by')
        
        if self.request.GET.get('year'):
            queryset = queryset.filter(year=self.request.GET.get('year'))
        if self.request.GET.get('status'):
            queryset = queryset.filter(status=self.request.GET.get('status'))
        
        return queryset.order_by('-year', 'name')
    
    def get_context_data(self):
        context = super().get_context_data()
        budgets = list(context['object_list'])
        context['total_requested'] = sum(b.total_requested for b in budgets)
        context['total_approved'] = sum(b.total_approved for b in budgets)
        context['total_spent'] = sum(b.spent_amount for b in budgets)
        return context


# =============================================================================
# EXPORTS ÉVÉNEMENTS
# =============================================================================

class EventsExportView(ExportPermissionMixin, BaseExportView):
    """Export des événements.
    
    Permissions: admin, secretariat
    """
    
    export_type = 'events'
    export_title = "Liste des Événements"
    export_filename_prefix = "evenements"
    
    def get_queryset(self):
        from apps.events.models import Event
        queryset = Event.objects.select_related('category', 'department', 'group', 'site')
        
        # Filtres par date
        if self.request.GET.get('date_from'):
            queryset = queryset.filter(start_date__gte=self.request.GET.get('date_from'))
        if self.request.GET.get('date_to'):
            queryset = queryset.filter(start_date__lte=self.request.GET.get('date_to'))
        
        # Autres filtres
        if self.request.GET.get('category_id'):
            queryset = queryset.filter(category_id=self.request.GET.get('category_id'))
        if self.request.GET.get('upcoming') == '1':
            from datetime import date
            queryset = queryset.filter(start_date__gte=date.today(), is_cancelled=False)
        
        return queryset.order_by('start_date', 'start_time')
    
    def get_headers(self):
        return [
            'Titre', 'Date début', 'Heure', 'Date fin', 'Lieu',
            'Catégorie', 'Département', 'Groupe', 'Visibilité', 'Annulé'
        ]
    
    def get_row_data(self, event):
        return {
            'Titre': event.title,
            'Date début': event.start_date.strftime('%d/%m/%Y'),
            'Heure': event.start_time.strftime('%H:%M') if event.start_time else 'Journée',
            'Date fin': event.end_date.strftime('%d/%m/%Y') if event.end_date else '',
            'Lieu': event.location,
            'Catégorie': str(event.category) if event.category else '',
            'Département': str(event.department) if event.department else '',
            'Groupe': str(event.group) if event.group else '',
            'Visibilité': event.get_visibility_display(),
            'Annulé': 'Oui' if event.is_cancelled else 'Non'
        }


class EventsPrintView(ExportPermissionMixin, BasePDFView):
    """Impression PDF de la liste des événements.
    
    Permissions: admin, secretariat
    """
    
    export_type = 'events'
    template_name = 'events/print/events_list.html'
    pdf_title = "Liste des Événements"
    pdf_filename_prefix = "evenements"
    
    def get_queryset(self):
        from apps.events.models import Event
        queryset = Event.objects.select_related('category', 'department', 'group')
        
        if self.request.GET.get('date_from'):
            queryset = queryset.filter(start_date__gte=self.request.GET.get('date_from'))
        if self.request.GET.get('date_to'):
            queryset = queryset.filter(start_date__lte=self.request.GET.get('date_to'))
        if self.request.GET.get('upcoming') == '1':
            from datetime import date
            queryset = queryset.filter(start_date__gte=date.today(), is_cancelled=False)
        
        return queryset.order_by('start_date', 'start_time')
    
    def get_context_data(self):
        context = super().get_context_data()
        context['total_events'] = context['object_list'].count()
        context['upcoming_events'] = context['object_list'].filter(is_cancelled=False).count()
        return context


# =============================================================================
# EXPORTS GROUPES
# =============================================================================

class GroupsExportView(ExportPermissionMixin, BaseExportView):
    """Export des groupes.
    
    Permissions: admin, secretariat, responsable_groupe
    """
    
    export_type = 'groups'
    export_title = "Liste des Groupes"
    export_filename_prefix = "groupes"
    
    def get_queryset(self):
        from apps.groups.models import Group
        queryset = Group.objects.select_related('leader', 'site').prefetch_related('members')
        
        if self.request.GET.get('type'):
            queryset = queryset.filter(group_type=self.request.GET.get('type'))
        if self.request.GET.get('active_only') == '1':
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('name')
    
    def get_headers(self):
        return [
            'Nom', 'Type', 'Responsable', 'Nb Membres', 'Jour de réunion',
            'Heure', 'Lieu', 'Fréquence', 'Actif'
        ]
    
    def get_row_data(self, group):
        return {
            'Nom': group.name,
            'Type': group.get_group_type_display(),
            'Responsable': group.leader.get_full_name() if group.leader else '',
            'Nb Membres': group.member_count,
            'Jour de réunion': dict(group._meta.get_field('meeting_day').choices).get(group.meeting_day, ''),
            'Heure': group.meeting_time.strftime('%H:%M') if group.meeting_time else '',
            'Lieu': group.meeting_location,
            'Fréquence': dict(group._meta.get_field('meeting_frequency').choices).get(group.meeting_frequency, ''),
            'Actif': 'Oui' if group.is_active else 'Non'
        }


class GroupMembersExportView(ExportPermissionMixin, BaseExportView):
    """Export des membres d'un groupe spécifique.
    
    Permissions: admin, secretariat, responsable_groupe
    """
    
    export_type = 'group_members'
    export_filename_prefix = "groupe_membres"
    
    def get_group(self):
        from apps.groups.models import Group
        return get_object_or_404(Group, pk=self.kwargs['pk'])
    
    def get_queryset(self):
        group = self.get_group()
        return group.members.all().order_by('last_name', 'first_name')
    
    def get_headers(self):
        return ['Nom', 'Prénom', 'Email', 'Téléphone', 'Statut']
    
    def get_row_data(self, member):
        return {
            'Nom': member.last_name,
            'Prénom': member.first_name,
            'Email': member.email,
            'Téléphone': member.phone,
            'Statut': member.get_status_display()
        }
    
    def get(self, request, *args, **kwargs):
        group = self.get_group()
        self.export_title = f"Membres du groupe - {group.name}"
        return super().get(request, *args, **kwargs)


class GroupsPrintView(ExportPermissionMixin, BasePDFView):
    """Impression PDF de la liste des groupes.
    
    Permissions: admin, secretariat, responsable_groupe
    """
    
    export_type = 'groups'
    template_name = 'groups/print/groups_list.html'
    pdf_title = "Liste des Groupes"
    pdf_filename_prefix = "groupes"
    
    def get_queryset(self):
        from apps.groups.models import Group
        queryset = Group.objects.select_related('leader').prefetch_related('members')
        
        if self.request.GET.get('type'):
            queryset = queryset.filter(group_type=self.request.GET.get('type'))
        if self.request.GET.get('active_only') == '1':
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('name')
    
    def get_context_data(self):
        context = super().get_context_data()
        groups = list(context['object_list'])
        context['total_groups'] = len(groups)
        context['total_members'] = sum(g.member_count for g in groups)
        return context


# =============================================================================
# EXPORTS PRÉSENCES (Club Biblique)
# =============================================================================

class AttendanceExportView(ExportPermissionMixin, BaseExportView):
    """Export des présences du club biblique.
    
    Permissions: admin, responsable_club
    Requirements: 4.2
    """
    
    export_type = 'attendance'
    export_title = "Présences - Club Biblique"
    export_filename_prefix = "presences_club_biblique"
    
    def get_queryset(self):
        from apps.bibleclub.models import Attendance
        queryset = Attendance.objects.select_related(
            'session', 'child', 'bible_class', 'bible_class__age_group'
        )
        
        # Filtres par date
        if self.request.GET.get('date_from'):
            queryset = queryset.filter(session__date__gte=self.request.GET.get('date_from'))
        if self.request.GET.get('date_to'):
            queryset = queryset.filter(session__date__lte=self.request.GET.get('date_to'))
        
        # Autres filtres
        if self.request.GET.get('class_id'):
            queryset = queryset.filter(bible_class_id=self.request.GET.get('class_id'))
        if self.request.GET.get('status'):
            queryset = queryset.filter(status=self.request.GET.get('status'))
        
        return queryset.order_by('-session__date', 'child__last_name')
    
    def get_headers(self):
        return [
            'Date', 'Enfant', 'Classe', 'Statut', 'Heure arrivée',
            'Heure départ', 'Récupéré par', 'Notes'
        ]
    
    def get_row_data(self, att):
        return {
            'Date': att.session.date.strftime('%d/%m/%Y'),
            'Enfant': att.child.full_name,
            'Classe': str(att.bible_class) if att.bible_class else '',
            'Statut': att.get_status_display(),
            'Heure arrivée': att.check_in_time.strftime('%H:%M') if att.check_in_time else '',
            'Heure départ': att.check_out_time.strftime('%H:%M') if att.check_out_time else '',
            'Récupéré par': att.picked_up_by,
            'Notes': att.notes[:50] + '...' if len(att.notes) > 50 else att.notes
        }


class AttendancePrintView(ExportPermissionMixin, BasePDFView):
    """Impression PDF des présences.
    
    Permissions: admin, responsable_club
    Requirements: 4.2
    """
    
    export_type = 'attendance'
    template_name = 'bibleclub/print/attendance_list.html'
    pdf_title = "Présences - Club Biblique"
    pdf_filename_prefix = "presences_club_biblique"
    
    def get_queryset(self):
        from apps.bibleclub.models import Attendance
        queryset = Attendance.objects.select_related(
            'session', 'child', 'bible_class'
        )
        
        if self.request.GET.get('date_from'):
            queryset = queryset.filter(session__date__gte=self.request.GET.get('date_from'))
        if self.request.GET.get('date_to'):
            queryset = queryset.filter(session__date__lte=self.request.GET.get('date_to'))
        if self.request.GET.get('session_id'):
            queryset = queryset.filter(session_id=self.request.GET.get('session_id'))
        
        return queryset.order_by('-session__date', 'child__last_name')
    
    def get_context_data(self):
        context = super().get_context_data()
        attendances = context['object_list']
        context['total_records'] = attendances.count()
        context['present_count'] = attendances.filter(status='present').count()
        context['absent_count'] = attendances.filter(status__in=['absent', 'absent_notified']).count()
        return context


# =============================================================================
# EXPORTS DÉPARTEMENTS
# =============================================================================

class DepartmentsExportView(ExportPermissionMixin, BaseExportView):
    """Export des départements.
    
    Permissions: admin, secretariat
    """
    
    export_type = 'departments'
    export_title = "Liste des Départements"
    export_filename_prefix = "departements"
    
    def get_queryset(self):
        from apps.departments.models import Department
        queryset = Department.objects.select_related('leader').prefetch_related('members')
        
        if self.request.GET.get('active_only') == '1':
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('name')
    
    def get_headers(self):
        return [
            'Nom', 'Description', 'Responsable', 'Nb Membres', 'Actif'
        ]
    
    def get_row_data(self, dept):
        return {
            'Nom': dept.name,
            'Description': dept.description[:100] if dept.description else '',
            'Responsable': dept.leader.get_full_name() if dept.leader else '',
            'Nb Membres': dept.members.count(),
            'Actif': 'Oui' if dept.is_active else 'Non'
        }


class DepartmentsPrintView(ExportPermissionMixin, BasePDFView):
    """Impression PDF des départements.
    
    Permissions: admin, secretariat
    """
    
    export_type = 'departments'
    template_name = 'departments/print/departments_list.html'
    pdf_title = "Liste des Départements"
    pdf_filename_prefix = "departements"
    
    def get_queryset(self):
        from apps.departments.models import Department
        queryset = Department.objects.select_related('leader').prefetch_related('members')
        
        if self.request.GET.get('active_only') == '1':
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('name')
    
    def get_context_data(self):
        context = super().get_context_data()
        depts = list(context['object_list'])
        context['total_departments'] = len(depts)
        context['total_members'] = sum(d.members.count() for d in depts)
        return context


# =============================================================================
# EXPORTS TRANSPORT
# =============================================================================

class DriversExportView(ExportPermissionMixin, BaseExportView):
    """Export des chauffeurs.
    
    Permissions: admin, secretariat
    """
    
    export_type = 'drivers'
    export_title = "Liste des Chauffeurs"
    export_filename_prefix = "chauffeurs"
    
    def get_queryset(self):
        from apps.transport.models import DriverProfile
        queryset = DriverProfile.objects.select_related('user')
        
        if self.request.GET.get('active_only') == '1':
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('user__last_name', 'user__first_name')
    
    def get_headers(self):
        return [
            'Nom', 'Téléphone', 'Véhicule', 'Places', 'Permis', 'Actif'
        ]
    
    def get_row_data(self, driver):
        return {
            'Nom': driver.user.get_full_name(),
            'Téléphone': driver.phone or '',
            'Véhicule': driver.vehicle_type or '',
            'Places': driver.vehicle_capacity or '',
            'Permis': driver.license_number or '',
            'Actif': 'Oui' if driver.is_active else 'Non'
        }


class DriversPrintView(ExportPermissionMixin, BasePDFView):
    """Impression PDF des chauffeurs.
    
    Permissions: admin, secretariat
    """
    
    export_type = 'drivers'
    template_name = 'transport/print/drivers_list.html'
    pdf_title = "Liste des Chauffeurs"
    pdf_filename_prefix = "chauffeurs"
    
    def get_queryset(self):
        from apps.transport.models import DriverProfile
        queryset = DriverProfile.objects.select_related('user')
        
        if self.request.GET.get('active_only') == '1':
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('user__last_name', 'user__first_name')
    
    def get_context_data(self):
        context = super().get_context_data()
        context['total_drivers'] = context['object_list'].count()
        context['active_drivers'] = context['object_list'].filter(is_active=True).count()
        return context


# =============================================================================
# EXPORTS INVENTAIRE
# =============================================================================

class InventoryExportView(ExportPermissionMixin, BaseExportView):
    """Export de l'inventaire.
    
    Permissions: admin, secretariat
    """
    
    export_type = 'inventory'
    export_title = "Inventaire"
    export_filename_prefix = "inventaire"
    
    def get_queryset(self):
        from apps.inventory.models import Item
        queryset = Item.objects.select_related('category', 'location')
        
        if self.request.GET.get('category_id'):
            queryset = queryset.filter(category_id=self.request.GET.get('category_id'))
        if self.request.GET.get('location_id'):
            queryset = queryset.filter(location_id=self.request.GET.get('location_id'))
        if self.request.GET.get('low_stock') == '1':
            queryset = queryset.filter(quantity__lte=models.F('min_quantity'))
        
        return queryset.order_by('name')
    
    def get_headers(self):
        return [
            'Nom', 'Catégorie', 'Quantité', 'Qté Min', 'Emplacement', 'État'
        ]
    
    def get_row_data(self, item):
        return {
            'Nom': item.name,
            'Catégorie': str(item.category) if item.category else '',
            'Quantité': item.quantity,
            'Qté Min': item.min_quantity or '',
            'Emplacement': str(item.location) if item.location else '',
            'État': item.get_condition_display() if hasattr(item, 'get_condition_display') else ''
        }


class InventoryPrintView(ExportPermissionMixin, BasePDFView):
    """Impression PDF de l'inventaire.
    
    Permissions: admin, secretariat
    """
    
    export_type = 'inventory'
    template_name = 'inventory/print/inventory_list.html'
    pdf_title = "Inventaire"
    pdf_filename_prefix = "inventaire"
    
    def get_queryset(self):
        from apps.inventory.models import Item
        queryset = Item.objects.select_related('category', 'location')
        
        if self.request.GET.get('category_id'):
            queryset = queryset.filter(category_id=self.request.GET.get('category_id'))
        if self.request.GET.get('location_id'):
            queryset = queryset.filter(location_id=self.request.GET.get('location_id'))
        
        return queryset.order_by('name')
    
    def get_context_data(self):
        context = super().get_context_data()
        context['total_items'] = context['object_list'].count()
        return context


# =============================================================================
# EXPORTS WORSHIP (Cultes)
# =============================================================================

class WorshipServicesExportView(ExportPermissionMixin, BaseExportView):
    """Export des cultes.
    
    Permissions: admin, responsable_groupe
    """
    
    export_type = 'worship'
    export_title = "Liste des Cultes"
    export_filename_prefix = "cultes"
    
    def get_queryset(self):
        from apps.worship.models import WorshipService
        queryset = WorshipService.objects.select_related('site')
        
        if self.request.GET.get('date_from'):
            queryset = queryset.filter(date__gte=self.request.GET.get('date_from'))
        if self.request.GET.get('date_to'):
            queryset = queryset.filter(date__lte=self.request.GET.get('date_to'))
        
        return queryset.order_by('-date')
    
    def get_headers(self):
        return [
            'Date', 'Type', 'Thème', 'Prédicateur', 'Site', 'Participants'
        ]
    
    def get_row_data(self, service):
        return {
            'Date': service.date.strftime('%d/%m/%Y'),
            'Type': service.get_service_type_display() if hasattr(service, 'get_service_type_display') else '',
            'Thème': service.theme or '',
            'Prédicateur': service.preacher or '',
            'Site': str(service.site) if service.site else '',
            'Participants': service.attendance_count or ''
        }


class WorshipServicesPrintView(ExportPermissionMixin, BasePDFView):
    """Impression PDF des cultes.
    
    Permissions: admin, responsable_groupe
    """
    
    export_type = 'worship'
    template_name = 'worship/print/services_list.html'
    pdf_title = "Liste des Cultes"
    pdf_filename_prefix = "cultes"
    
    def get_queryset(self):
        from apps.worship.models import WorshipService
        queryset = WorshipService.objects.select_related('site')
        
        if self.request.GET.get('date_from'):
            queryset = queryset.filter(date__gte=self.request.GET.get('date_from'))
        if self.request.GET.get('date_to'):
            queryset = queryset.filter(date__lte=self.request.GET.get('date_to'))
        
        return queryset.order_by('-date')
    
    def get_context_data(self):
        context = super().get_context_data()
        context['total_services'] = context['object_list'].count()
        return context


# =============================================================================
# EXPORTS UTILISATEURS
# =============================================================================

class UsersExportView(ExportPermissionMixin, BaseExportView):
    """Export des utilisateurs.
    
    Permissions: admin uniquement
    """
    
    export_type = 'users'
    export_title = "Liste des Utilisateurs"
    export_filename_prefix = "utilisateurs"
    
    def get_queryset(self):
        from apps.accounts.models import User
        queryset = User.objects.all()
        
        if self.request.GET.get('active_only') == '1':
            queryset = queryset.filter(is_active=True)
        if self.request.GET.get('role'):
            queryset = queryset.filter(role=self.request.GET.get('role'))
        
        return queryset.order_by('last_name', 'first_name')
    
    def get_headers(self):
        return [
            'Nom', 'Prénom', 'Email', 'Rôle', 'Actif', 'Dernière connexion'
        ]
    
    def get_row_data(self, user):
        return {
            'Nom': user.last_name,
            'Prénom': user.first_name,
            'Email': user.email,
            'Rôle': user.get_role_display() if hasattr(user, 'get_role_display') else user.role,
            'Actif': 'Oui' if user.is_active else 'Non',
            'Dernière connexion': user.last_login.strftime('%d/%m/%Y %H:%M') if user.last_login else 'Jamais'
        }


class UsersPrintView(ExportPermissionMixin, BasePDFView):
    """Impression PDF des utilisateurs.
    
    Permissions: admin uniquement
    """
    
    export_type = 'users'
    template_name = 'accounts/print/users_list.html'
    pdf_title = "Liste des Utilisateurs"
    pdf_filename_prefix = "utilisateurs"
    
    def get_queryset(self):
        from apps.accounts.models import User
        queryset = User.objects.all()
        
        if self.request.GET.get('active_only') == '1':
            queryset = queryset.filter(is_active=True)
        if self.request.GET.get('role'):
            queryset = queryset.filter(role=self.request.GET.get('role'))
        
        return queryset.order_by('last_name', 'first_name')
    
    def get_context_data(self):
        context = super().get_context_data()
        context['total_users'] = context['object_list'].count()
        context['active_users'] = context['object_list'].filter(is_active=True).count()
        return context
