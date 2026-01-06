"""
Vues Kanban pour la gestion des visites pastorales.

Permet de visualiser et gérer les visites sous forme de tableau Kanban
avec colonnes : Planifié, À faire, En cours, Effectué.
"""

from django.shortcuts import render, get_object_or_404
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
import json

from .models import VisitationLog, Member, LifeEvent
from apps.core.permissions import RoleRequiredMixin


class KanbanBoardView(RoleRequiredMixin, LoginRequiredMixin, TemplateView):
    """Vue principale du tableau Kanban des visites."""
    template_name = 'members/kanban_board.html'
    allowed_roles = ('admin', 'secretariat', 'encadrant')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Colonnes du Kanban
        context['columns'] = [
            {
                'id': 'planifie',
                'title': 'Planifié',
                'status': VisitationLog.Status.PLANIFIE,
                'color': 'info',
                'icon': 'bi-calendar-event',
            },
            {
                'id': 'a_faire',
                'title': 'À faire',
                'status': VisitationLog.Status.A_FAIRE,
                'color': 'warning',
                'icon': 'bi-exclamation-circle',
            },
            {
                'id': 'effectue',
                'title': 'Effectué',
                'status': VisitationLog.Status.EFFECTUE,
                'color': 'success',
                'icon': 'bi-check-circle',
            },
            {
                'id': 'reporte',
                'title': 'Reporté',
                'status': VisitationLog.Status.REPORTE,
                'color': 'secondary',
                'icon': 'bi-arrow-repeat',
            },
        ]
        
        # Charger les visites par colonne
        for column in context['columns']:
            column['visits'] = VisitationLog.objects.filter(
                status=column['status']
            ).select_related('member', 'visitor', 'life_event').order_by(
                '-scheduled_date', '-visit_date'
            )[:20]
        
        # Membres nécessitant une visite
        context['members_needing_visit'] = self._get_members_needing_visit()
        
        # Événements de vie récents non traités
        context['pending_life_events'] = LifeEvent.objects.filter(
            requires_visit=True,
            visit_completed=False
        ).select_related('primary_member').order_by('-event_date')[:10]
        
        # Statistiques
        context['stats'] = self._get_stats()
        
        return context
    
    def _get_members_needing_visit(self):
        """Retourne les membres qui n'ont pas été visités depuis longtemps."""
        members = []
        for member in Member.objects.filter(status='actif'):
            if member.needs_visit:
                members.append({
                    'member': member,
                    'days': member.days_since_last_visit,
                    'last_visit': member.last_visit_date,
                })
        
        # Trier par nombre de jours (les plus anciens en premier)
        members.sort(key=lambda x: x['days'] if x['days'] else 9999, reverse=True)
        return members[:15]
    
    def _get_stats(self):
        """Calcule les statistiques des visites."""
        from datetime import timedelta
        from django.db.models import Count
        
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        return {
            'total_this_month': VisitationLog.objects.filter(
                visit_date__gte=month_start,
                status=VisitationLog.Status.EFFECTUE
            ).count(),
            'pending': VisitationLog.objects.filter(
                status__in=[VisitationLog.Status.PLANIFIE, VisitationLog.Status.A_FAIRE]
            ).count(),
            'overdue': VisitationLog.objects.filter(
                status=VisitationLog.Status.PLANIFIE,
                scheduled_date__lt=today
            ).count(),
        }


class KanbanUpdateView(RoleRequiredMixin, LoginRequiredMixin, View):
    """API pour mettre à jour le statut d'une visite (drag & drop)."""
    allowed_roles = ('admin', 'secretariat', 'encadrant')
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            visit_id = data.get('visit_id')
            new_status = data.get('status')
            
            visit = get_object_or_404(VisitationLog, id=visit_id)
            
            # Mettre à jour le statut
            visit.status = new_status
            
            # Si marqué comme effectué, mettre à jour la date
            if new_status == VisitationLog.Status.EFFECTUE:
                if not visit.visit_date:
                    visit.visit_date = timezone.now().date()
                
                # Marquer l'événement de vie comme visité si lié
                if visit.life_event:
                    visit.life_event.visit_completed = True
                    visit.life_event.save()
            
            visit.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Visite mise à jour: {visit.get_status_display()}'
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


class QuickVisitCreateView(RoleRequiredMixin, LoginRequiredMixin, View):
    """Création rapide d'une visite depuis le Kanban."""
    allowed_roles = ('admin', 'secretariat', 'encadrant')
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            member_id = data.get('member_id')
            visit_type = data.get('visit_type', 'domicile')
            scheduled_date = data.get('scheduled_date')
            life_event_id = data.get('life_event_id')
            
            member = get_object_or_404(Member, id=member_id)
            
            visit = VisitationLog.objects.create(
                member=member,
                visitor=request.user,
                visit_type=visit_type,
                status=VisitationLog.Status.PLANIFIE,
                scheduled_date=scheduled_date,
                life_event_id=life_event_id if life_event_id else None,
            )
            
            return JsonResponse({
                'success': True,
                'visit_id': visit.id,
                'message': f'Visite planifiée pour {member.full_name}'
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
