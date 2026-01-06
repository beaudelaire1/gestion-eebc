from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from datetime import date, timedelta
from .models import Member, LifeEvent, VisitationLog
from apps.core.permissions import role_required


@login_required
def member_list(request):
    """Liste des membres avec recherche et filtrage."""
    members_qs = Member.objects.all()
    
    # Statistiques
    total_count = members_qs.count()
    actifs_count = members_qs.filter(status='actif').count()
    baptises_count = members_qs.filter(is_baptized=True).count()
    hommes_count = members_qs.filter(gender='M').count()
    femmes_count = members_qs.filter(gender='F').count()
    
    # Recherche
    search = request.GET.get('search', '')
    if search:
        members_qs = members_qs.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )
    
    # Filtrage par statut
    status = request.GET.get('status', '')
    if status:
        members_qs = members_qs.filter(status=status)
    
    # Tri
    sort_by = request.GET.get('sort', 'last_name')
    sort_order = request.GET.get('order', 'asc')
    
    # Champs de tri autorisés
    allowed_sort_fields = ['last_name', 'first_name', 'email', 'city', 'status', 'birth_date']
    if sort_by not in allowed_sort_fields:
        sort_by = 'last_name'
    
    # Appliquer le tri
    if sort_order == 'desc':
        sort_by = f'-{sort_by}'
    
    members_qs = members_qs.order_by(sort_by, 'first_name')
    
    # Pagination
    paginator = Paginator(members_qs, 25)
    page = request.GET.get('page')
    members = paginator.get_page(page)
    
    context = {
        'members': members,
        'search': search,
        'status': status,
        'status_choices': Member.Status.choices,
        'total_count': total_count,
        'actifs_count': actifs_count,
        'baptises_count': baptises_count,
        'hommes_count': hommes_count,
        'femmes_count': femmes_count,
        'current_sort': request.GET.get('sort', 'last_name'),
        'current_order': request.GET.get('order', 'asc'),
    }
    
    if request.htmx:
        return render(request, 'members/partials/member_list_content.html', context)
    return render(request, 'members/member_list.html', context)


@login_required
def member_detail(request, pk):
    """Détail d'un membre."""
    member = get_object_or_404(Member, pk=pk)
    
    context = {
        'member': member,
    }
    
    # Récupérer les événements de vie et visites seulement pour les rôles autorisés
    from apps.core.permissions import has_role
    if has_role(request.user, 'admin', 'secretariat', 'encadrant'):
        life_events = member.life_events.all().order_by('-event_date')[:5]
        visits = member.visits_received.all().order_by('-visit_date')[:5]
        context.update({
            'life_events': life_events,
            'visits': visits,
            'can_view_pastoral_data': True,
        })
    
    return render(request, 'members/member_detail.html', context)


# =============================================================================
# VUES PASTORAL CRM - Événements de vie
# =============================================================================

@login_required
@role_required('admin', 'secretariat', 'encadrant')
def life_event_list(request):
    """Liste des événements de vie."""
    events = LifeEvent.objects.select_related('primary_member').order_by('-event_date')
    
    # Filtres
    event_type = request.GET.get('type')
    if event_type:
        events = events.filter(event_type=event_type)
    
    needs_visit = request.GET.get('needs_visit')
    if needs_visit == '1':
        events = events.filter(requires_visit=True, visit_completed=False)
    
    # Stats
    stats = {
        'total': events.count(),
        'pending_visits': events.filter(requires_visit=True, visit_completed=False).count(),
        'to_announce': events.filter(announce_sunday=True, announced=False).count(),
    }
    
    # Pagination
    paginator = Paginator(events, 20)
    page = request.GET.get('page')
    events = paginator.get_page(page)
    
    context = {
        'events': events,
        'event_types': LifeEvent.EventType.choices,
        'current_type': event_type,
        'stats': stats,
    }
    return render(request, 'members/life_event_list.html', context)


@login_required
@role_required('admin', 'secretariat', 'encadrant')
def life_event_create(request):
    """Créer un événement de vie."""
    from .forms import LifeEventForm
    
    if request.method == 'POST':
        form = LifeEventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.recorded_by = request.user
            event.save()
            form.save_m2m()
            messages.success(request, f"Événement '{event.title}' créé avec succès.")
            return redirect('members:life_events')
    else:
        form = LifeEventForm()
        # Pré-remplir le membre si passé en paramètre
        member_id = request.GET.get('member')
        if member_id:
            form.fields['primary_member'].initial = member_id
    
    return render(request, 'members/life_event_form.html', {'form': form})


@login_required
@role_required('admin', 'secretariat', 'encadrant')
def life_event_detail(request, pk):
    """Détail d'un événement de vie."""
    event = get_object_or_404(
        LifeEvent.objects.select_related('primary_member', 'recorded_by'),
        pk=pk
    )
    visits = event.visits.all().order_by('-visit_date')
    
    context = {
        'event': event,
        'visits': visits,
    }
    return render(request, 'members/life_event_detail.html', context)


@login_required
@role_required('admin', 'secretariat', 'encadrant')
def life_event_mark_visited(request, pk):
    """Marquer un événement comme visité."""
    event = get_object_or_404(LifeEvent, pk=pk)
    event.visit_completed = True
    event.save()
    messages.success(request, "Événement marqué comme visité.")
    
    if request.htmx:
        return HttpResponse('<span class="badge bg-success">Visité ✓</span>')
    return redirect('members:life_event_detail', pk=pk)


@login_required
@role_required('admin', 'secretariat', 'encadrant')
def life_event_mark_announced(request, pk):
    """Marquer un événement comme annoncé."""
    event = get_object_or_404(LifeEvent, pk=pk)
    event.announced = True
    event.save()
    messages.success(request, "Événement marqué comme annoncé.")
    
    if request.htmx:
        return HttpResponse('<span class="badge bg-success">Annoncé ✓</span>')
    return redirect('members:life_event_detail', pk=pk)


# =============================================================================
# VUES PASTORAL CRM - Visites pastorales
# =============================================================================

@login_required
@role_required('admin', 'secretariat', 'encadrant')
def visit_list(request):
    """Liste des visites pastorales."""
    visits = VisitationLog.objects.select_related('member', 'visitor').order_by('-visit_date', '-scheduled_date')
    
    # Filtres
    status = request.GET.get('status')
    if status:
        visits = visits.filter(status=status)
    
    visit_type = request.GET.get('type')
    if visit_type:
        visits = visits.filter(visit_type=visit_type)
    
    # Stats
    stats = {
        'total': visits.count(),
        'pending': visits.filter(status__in=['planifie', 'a_faire']).count(),
        'completed_month': visits.filter(
            status='effectue',
            visit_date__gte=date.today().replace(day=1)
        ).count(),
    }
    
    # Pagination
    paginator = Paginator(visits, 20)
    page = request.GET.get('page')
    visits = paginator.get_page(page)
    
    context = {
        'visits': visits,
        'statuses': VisitationLog.Status.choices,
        'visit_types': VisitationLog.VisitType.choices,
        'current_status': status,
        'current_type': visit_type,
        'stats': stats,
    }
    return render(request, 'members/visit_list.html', context)


@login_required
@role_required('admin', 'secretariat', 'encadrant')
def visit_create(request):
    """Créer une visite pastorale."""
    from .forms import VisitationLogForm
    
    if request.method == 'POST':
        form = VisitationLogForm(request.POST)
        if form.is_valid():
            visit = form.save(commit=False)
            if not visit.visitor:
                visit.visitor = request.user
            visit.save()
            messages.success(request, f"Visite pour {visit.member} créée.")
            return redirect('members:visits')
    else:
        form = VisitationLogForm()
        # Pré-remplir le membre si passé en paramètre
        member_id = request.GET.get('member')
        if member_id:
            form.fields['member'].initial = member_id
        # Pré-remplir l'événement de vie si passé
        event_id = request.GET.get('event')
        if event_id:
            form.fields['life_event'].initial = event_id
    
    return render(request, 'members/visit_form.html', {'form': form})


@login_required
@role_required('admin', 'secretariat', 'encadrant')
def visit_detail(request, pk):
    """Détail d'une visite."""
    visit = get_object_or_404(
        VisitationLog.objects.select_related('member', 'visitor', 'life_event'),
        pk=pk
    )
    return render(request, 'members/visit_detail.html', {'visit': visit})


@login_required
@role_required('admin', 'secretariat', 'encadrant')
def visit_complete(request, pk):
    """Marquer une visite comme effectuée."""
    visit = get_object_or_404(VisitationLog, pk=pk)
    visit.status = VisitationLog.Status.EFFECTUE
    visit.visit_date = date.today()
    visit.save()
    
    # Marquer l'événement de vie comme visité si lié
    if visit.life_event:
        visit.life_event.visit_completed = True
        visit.life_event.save()
    
    messages.success(request, "Visite marquée comme effectuée.")
    
    if request.htmx:
        return HttpResponse('<span class="badge bg-success">Effectuée ✓</span>')
    return redirect('members:visit_detail', pk=pk)


@login_required
@role_required('admin', 'secretariat', 'encadrant')
def members_needing_visit(request):
    """Liste des membres nécessitant une visite (pas visités depuis 6 mois)."""
    members = []
    six_months_ago = date.today() - timedelta(days=180)
    
    for member in Member.objects.filter(status='actif'):
        last_visit = member.last_visit_date
        if last_visit is None or last_visit < six_months_ago:
            members.append({
                'member': member,
                'last_visit': last_visit,
                'days_since': member.days_since_last_visit,
            })
    
    # Trier par ancienneté de visite
    members.sort(key=lambda x: x['days_since'] if x['days_since'] else 9999, reverse=True)
    
    context = {
        'members': members,
        'total': len(members),
    }
    return render(request, 'members/members_needing_visit.html', context)
