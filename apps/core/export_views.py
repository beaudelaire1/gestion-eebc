"""
Module d'export et d'impression générique.

Ce module fournit des vues génériques pour :
- Export Excel de toutes les données
- Génération PDF avec WeasyPrint
"""

from django.views.generic import View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
import json

from .services import ExportService
from .pdf_service import PDFService


class BaseExportView(LoginRequiredMixin, View):
    """Vue de base pour les exports Excel."""
    
    model = None
    export_title = "Export"
    export_filename_prefix = "export"
    
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

class ChildrenExportView(BaseExportView):
    """Export des enfants du club biblique."""
    
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


class ChildrenPrintView(BasePDFView):
    """Impression PDF de la liste des enfants."""
    
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

class MembersExportView(BaseExportView):
    """Export des membres de l'église."""
    
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


class MembersPrintView(BasePDFView):
    """Impression PDF de la liste des membres."""
    
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

class BudgetsExportView(BaseExportView):
    """Export des budgets."""
    
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


class BudgetDetailExportView(BaseExportView):
    """Export détaillé d'un budget avec ses lignes."""
    
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


class TransactionsExportView(BaseExportView):
    """Export des transactions financières."""
    
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


class BudgetsPrintView(BasePDFView):
    """Impression PDF de la liste des budgets."""
    
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

class EventsExportView(BaseExportView):
    """Export des événements."""
    
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


class EventsPrintView(BasePDFView):
    """Impression PDF de la liste des événements."""
    
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

class GroupsExportView(BaseExportView):
    """Export des groupes."""
    
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


class GroupMembersExportView(BaseExportView):
    """Export des membres d'un groupe spécifique."""
    
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


class GroupsPrintView(BasePDFView):
    """Impression PDF de la liste des groupes."""
    
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

class AttendanceExportView(BaseExportView):
    """Export des présences du club biblique."""
    
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


class AttendancePrintView(BasePDFView):
    """Impression PDF des présences."""
    
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

class DepartmentsExportView(BaseExportView):
    """Export des départements."""
    
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


class DepartmentsPrintView(BasePDFView):
    """Impression PDF des départements."""
    
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

class DriversExportView(BaseExportView):
    """Export des chauffeurs."""
    
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


class DriversPrintView(BasePDFView):
    """Impression PDF des chauffeurs."""
    
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

class InventoryExportView(BaseExportView):
    """Export de l'inventaire."""
    
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


class InventoryPrintView(BasePDFView):
    """Impression PDF de l'inventaire."""
    
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

class WorshipServicesExportView(BaseExportView):
    """Export des cultes."""
    
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


class WorshipServicesPrintView(BasePDFView):
    """Impression PDF des cultes."""
    
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

class UsersExportView(BaseExportView):
    """Export des utilisateurs."""
    
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


class UsersPrintView(BasePDFView):
    """Impression PDF des utilisateurs."""
    
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
