"""Security boundary for member and pastoral data."""
from __future__ import annotations

import json
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.permissions import role_required
from apps.core.security import can_view_confidential_pastoral_data
from . import views as legacy_views
from . import kanban_views as legacy_kanban
from .models import LifeEvent, Member, VisitationLog


STAFF_ROLES = ('admin', 'secretariat', 'encadrant', 'pasteur')


def _visible_visits(user, queryset=None):
    queryset = queryset if queryset is not None else VisitationLog.objects.all()
    if can_view_confidential_pastoral_data(user):
        return queryset
    return queryset.filter(is_confidential=False)


@login_required
@role_required(*STAFF_ROLES)
def member_list(request):
    # The legacy template exposes phone/email/profession. Restrict the complete
    # directory instead of pretending that hiding action buttons protects data.
    return legacy_views.member_list(request)


@login_required
@role_required(*STAFF_ROLES)
def member_detail(request, pk):
    member = get_object_or_404(Member, pk=pk)
    life_events = member.life_events.all().order_by('-event_date')[:5]
    visits = _visible_visits(
        request.user,
        member.visits_received.all().order_by('-visit_date'),
    )[:5]
    return render(request, 'members/member_detail.html', {
        'member': member,
        'life_events': life_events,
        'visits': visits,
        'can_view_pastoral_data': True,
    })


@login_required
@role_required(*STAFF_ROLES)
def member_print_registration(request, pk):
    return legacy_views.member_print_registration(request, pk)


@login_required
@role_required(*STAFF_ROLES)
def life_event_detail(request, pk):
    event = get_object_or_404(
        LifeEvent.objects.select_related('primary_member', 'recorded_by'),
        pk=pk,
    )
    visits = _visible_visits(
        request.user,
        event.visits.all().order_by('-visit_date'),
    )
    return render(request, 'members/life_event_detail.html', {
        'event': event,
        'visits': visits,
    })


@login_required
@role_required(*STAFF_ROLES)
def visit_list(request):
    visits = _visible_visits(
        request.user,
        VisitationLog.objects.select_related('member', 'visitor').order_by('-visit_date', '-scheduled_date'),
    )
    visit_status = request.GET.get('status')
    visit_type = request.GET.get('type')
    if visit_status:
        visits = visits.filter(status=visit_status)
    if visit_type:
        visits = visits.filter(visit_type=visit_type)

    stats = {
        'total': visits.count(),
        'pending': visits.filter(status__in=['planifie', 'a_faire']).count(),
        'completed_month': visits.filter(
            status='effectue',
            visit_date__gte=date.today().replace(day=1),
        ).count(),
    }
    page = Paginator(visits, 20).get_page(request.GET.get('page'))
    return render(request, 'members/visit_list.html', {
        'visits': page,
        'statuses': VisitationLog.Status.choices,
        'visit_types': VisitationLog.VisitType.choices,
        'current_status': visit_status,
        'current_type': visit_type,
        'stats': stats,
    })


@login_required
@role_required(*STAFF_ROLES)
def visit_detail(request, pk):
    visit = get_object_or_404(
        VisitationLog.objects.select_related('member', 'visitor', 'life_event'),
        pk=pk,
    )
    if visit.is_confidential and not can_view_confidential_pastoral_data(request.user):
        raise Http404
    return render(request, 'members/visit_detail.html', {'visit': visit})


@login_required
@role_required(*STAFF_ROLES)
@require_POST
def life_event_mark_visited(request, pk):
    event = get_object_or_404(LifeEvent, pk=pk)
    event.visit_completed = True
    event.save(update_fields=['visit_completed'])
    messages.success(request, 'Événement marqué comme visité.')
    if request.htmx:
        return HttpResponse('<span class="badge bg-success">Visité ✓</span>')
    return redirect('members:life_event_detail', pk=pk)


@login_required
@role_required(*STAFF_ROLES)
@require_POST
def life_event_mark_announced(request, pk):
    event = get_object_or_404(LifeEvent, pk=pk)
    event.announced = True
    event.save(update_fields=['announced'])
    messages.success(request, 'Événement marqué comme annoncé.')
    if request.htmx:
        return HttpResponse('<span class="badge bg-success">Annoncé ✓</span>')
    return redirect('members:life_event_detail', pk=pk)


@login_required
@role_required(*STAFF_ROLES)
@require_POST
def visit_complete(request, pk):
    visit = get_object_or_404(VisitationLog, pk=pk)
    if visit.is_confidential and not can_view_confidential_pastoral_data(request.user):
        raise Http404
    visit.status = VisitationLog.Status.EFFECTUE
    visit.visit_date = date.today()
    visit.save(update_fields=['status', 'visit_date'])
    if visit.life_event:
        visit.life_event.visit_completed = True
        visit.life_event.save(update_fields=['visit_completed'])
    messages.success(request, 'Visite marquée comme effectuée.')
    if request.htmx:
        return HttpResponse('<span class="badge bg-success">Effectuée ✓</span>')
    return redirect('members:visit_detail', pk=pk)


class SecureKanbanBoardView(legacy_kanban.KanbanBoardView):
    allowed_roles = STAFF_ROLES

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if can_view_confidential_pastoral_data(self.request.user):
            return context
        for column in context.get('columns', []):
            column['visits'] = [
                visit for visit in column.get('visits', []) if not visit.is_confidential
            ]
        visible = VisitationLog.objects.filter(is_confidential=False)
        today = timezone.now().date()
        month_start = today.replace(day=1)
        context['stats'] = {
            'total_this_month': visible.filter(
                visit_date__gte=month_start,
                status=VisitationLog.Status.EFFECTUE,
            ).count(),
            'pending': visible.filter(
                status__in=[VisitationLog.Status.PLANIFIE, VisitationLog.Status.A_FAIRE],
            ).count(),
            'overdue': visible.filter(
                status=VisitationLog.Status.PLANIFIE,
                scheduled_date__lt=today,
            ).count(),
        }
        return context


class SecureKanbanUpdateView(legacy_kanban.KanbanUpdateView):
    allowed_roles = STAFF_ROLES

    def post(self, request):
        try:
            payload = json.loads(request.body or '{}')
            visit = VisitationLog.objects.filter(pk=payload.get('visit_id')).first()
        except (TypeError, ValueError, json.JSONDecodeError):
            visit = None
        if visit and visit.is_confidential and not can_view_confidential_pastoral_data(request.user):
            return JsonResponse({'success': False, 'error': 'Accès refusé'}, status=403)
        return super().post(request)


class SecureQuickVisitCreateView(legacy_kanban.QuickVisitCreateView):
    allowed_roles = STAFF_ROLES
