"""
Vues du module Jeunesse.

CRUD complet pour les jeunes, groupes, activités et présences.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone

from apps.core.permissions import role_required
from .models import YoungMember, YouthGroup, YouthEvent, YouthAttendance
from .forms import (
    YoungMemberForm, YouthGroupForm, YouthEventForm, YoungMemberSearchForm,
)
import logging

logger = logging.getLogger(__name__)


YOUNG_ROLES = ('admin', 'secretariat', 'responsable_groupe', 'pasteur')


# =============================================================================
# TABLEAU DE BORD
# =============================================================================

@login_required
@role_required(*YOUNG_ROLES)
def young_home(request):
    """Page d'accueil du module jeunesse."""
    stats = {
        'total_young': YoungMember.objects.filter(is_active=True).count(),
        'total_groups': YouthGroup.objects.filter(is_active=True).count(),
        'total_baptized': YoungMember.objects.filter(is_active=True, is_baptized=True).count(),
        'total_transport': YoungMember.objects.filter(is_active=True, needs_transport=True).count(),
    }

    recent_events = YouthEvent.objects.filter(
        is_cancelled=False,
    ).order_by('-date')[:5]

    recent_members = YoungMember.objects.filter(
        is_active=True,
    ).order_by('-created_at')[:5]

    context = {
        'stats': stats,
        'recent_events': recent_events,
        'recent_members': recent_members,
    }
    return render(request, 'young/home.html', context)


# =============================================================================
# JEUNES — CRUD
# =============================================================================

@login_required
@role_required(*YOUNG_ROLES)
def young_member_list(request):
    """Liste des jeunes avec filtres."""
    form = YoungMemberSearchForm(request.GET)
    members = YoungMember.objects.select_related('group', 'site', 'assigned_driver')

    if form.is_valid():
        search = form.cleaned_data.get('search')
        if search:
            members = members.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search)
            )

        group = form.cleaned_data.get('group')
        if group:
            members = members.filter(group=group)

        status = form.cleaned_data.get('status')
        if status:
            members = members.filter(status=status)

        baptized = form.cleaned_data.get('baptized')
        if baptized == 'yes':
            members = members.filter(is_baptized=True)
        elif baptized == 'no':
            members = members.filter(is_baptized=False)

        transport = form.cleaned_data.get('transport')
        if transport == 'yes':
            members = members.filter(needs_transport=True)
        elif transport == 'no':
            members = members.filter(needs_transport=False)

    paginator = Paginator(members, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'form': form,
        'total_count': members.count(),
        'groups': YouthGroup.objects.filter(is_active=True),
    }
    return render(request, 'young/young_member_list.html', context)


@login_required
@role_required(*YOUNG_ROLES)
def young_member_detail(request, pk):
    """Fiche détaillée d'un jeune."""
    member = get_object_or_404(
        YoungMember.objects.select_related('group', 'site', 'family', 'assigned_driver'),
        pk=pk,
    )

    # Statistiques de présence
    attendances = YouthAttendance.objects.filter(young_member=member)
    total_events = attendances.count()
    present_count = attendances.filter(
        status__in=[YouthAttendance.Status.PRESENT, YouthAttendance.Status.RETARD]
    ).count()
    attendance_rate = (present_count / total_events * 100) if total_events > 0 else 0

    # Dernières présences
    recent_attendances = attendances.select_related('event').order_by('-event__date')[:10]

    context = {
        'member': member,
        'total_events': total_events,
        'present_count': present_count,
        'attendance_rate': attendance_rate,
        'recent_attendances': recent_attendances,
    }
    return render(request, 'young/young_member_detail.html', context)


@login_required
@role_required(*YOUNG_ROLES)
def young_member_create(request):
    """Inscrire un nouveau jeune."""
    if request.method == 'POST':
        form = YoungMemberForm(request.POST, request.FILES)
        if form.is_valid():
            member = form.save()
            messages.success(request, f"{member.full_name} a été inscrit(e) avec succès.")
            return redirect('young:member_detail', pk=member.pk)
    else:
        form = YoungMemberForm()

    return render(request, 'young/young_member_form.html', {
        'form': form,
        'title': 'Inscrire un jeune',
        'is_creation': True,
    })


@login_required
@role_required(*YOUNG_ROLES)
def young_member_edit(request, pk):
    """Modifier la fiche d'un jeune."""
    member = get_object_or_404(YoungMember, pk=pk)

    if request.method == 'POST':
        form = YoungMemberForm(request.POST, request.FILES, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, f"Fiche de {member.full_name} mise à jour.")
            return redirect('young:member_detail', pk=member.pk)
    else:
        form = YoungMemberForm(instance=member)

    return render(request, 'young/young_member_form.html', {
        'form': form,
        'member': member,
        'title': f'Modifier {member.full_name}',
        'is_creation': False,
    })


@login_required
@role_required('admin', 'secretariat')
def young_member_delete(request, pk):
    """Désactiver un jeune (soft delete)."""
    member = get_object_or_404(YoungMember, pk=pk)

    if request.method == 'POST':
        member.is_active = False
        member.status = YoungMember.Status.INACTIF
        member.save(update_fields=['is_active', 'status', 'updated_at'])
        messages.success(request, f"{member.full_name} a été désactivé(e).")
        return redirect('young:member_list')

    context = {
        'member': member,
        'title': f'Désactiver {member.full_name}',
    }
    return render(request, 'young/young_member_confirm_delete.html', context)


# =============================================================================
# GROUPES — CRUD
# =============================================================================

@login_required
@role_required('admin', 'secretariat')
def group_list(request):
    """Liste des groupes de jeunesse."""
    groups = YouthGroup.objects.annotate(
        member_count=Count('young_members', filter=Q(young_members__is_active=True))
    ).order_by('min_age')

    return render(request, 'young/group_list.html', {'groups': groups})


@login_required
@role_required('admin', 'secretariat')
def group_create(request):
    """Créer un groupe de jeunesse."""
    if request.method == 'POST':
        form = YouthGroupForm(request.POST)
        if form.is_valid():
            group = form.save()
            messages.success(request, f'Groupe « {group.name} » créé.')
            return redirect('young:group_list')
    else:
        form = YouthGroupForm()

    return render(request, 'young/group_form.html', {
        'form': form,
        'title': 'Nouveau groupe',
    })


@login_required
@role_required('admin', 'secretariat')
def group_edit(request, pk):
    """Modifier un groupe de jeunesse."""
    group = get_object_or_404(YouthGroup, pk=pk)

    if request.method == 'POST':
        form = YouthGroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, f'Groupe « {group.name} » modifié.')
            return redirect('young:group_list')
    else:
        form = YouthGroupForm(instance=group)

    return render(request, 'young/group_form.html', {
        'form': form,
        'group': group,
        'title': f'Modifier {group.name}',
    })


@login_required
@role_required('admin')
def group_delete(request, pk):
    """Supprimer un groupe de jeunesse."""
    group = get_object_or_404(YouthGroup, pk=pk)

    if request.method == 'POST':
        name = group.name
        group.is_active = False
        group.save(update_fields=['is_active'])
        messages.success(request, f'Groupe « {name} » désactivé.')
        return redirect('young:group_list')

    return render(request, 'young/group_confirm_delete.html', {
        'group': group,
        'title': f'Désactiver {group.name}',
        'member_count': group.young_members.filter(is_active=True).count(),
    })


# =============================================================================
# ACTIVITÉS — CRUD
# =============================================================================

@login_required
@role_required(*YOUNG_ROLES)
def event_list(request):
    """Liste des activités jeunesse."""
    events = YouthEvent.objects.select_related('site', 'created_by').annotate(
        attendance_count=Count(
            'attendances',
            filter=Q(attendances__status__in=['present', 'retard']),
        ),
    )

    # Filtres
    event_type = request.GET.get('type')
    if event_type:
        events = events.filter(event_type=event_type)

    upcoming = request.GET.get('upcoming')
    if upcoming == '1':
        events = events.filter(date__gte=timezone.now().date())

    paginator = Paginator(events, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'event_types': YouthEvent.EventType.choices,
        'current_type': event_type,
    }
    return render(request, 'young/event_list.html', context)


@login_required
@role_required(*YOUNG_ROLES)
def event_detail(request, pk):
    """Détail d'une activité avec liste de présence."""
    event = get_object_or_404(YouthEvent.objects.select_related('site', 'created_by'), pk=pk)

    attendances = YouthAttendance.objects.filter(
        event=event,
    ).select_related('young_member', 'young_member__group')

    stats = {
        'present': attendances.filter(status=YouthAttendance.Status.PRESENT).count(),
        'absent': attendances.filter(status=YouthAttendance.Status.ABSENT).count(),
        'excuse': attendances.filter(status=YouthAttendance.Status.EXCUSE).count(),
        'retard': attendances.filter(status=YouthAttendance.Status.RETARD).count(),
        'transported': attendances.filter(transported=True).count(),
    }

    context = {
        'event': event,
        'attendances': attendances,
        'stats': stats,
    }
    return render(request, 'young/event_detail.html', context)


@login_required
@role_required(*YOUNG_ROLES)
def event_create(request):
    """Créer une activité jeunesse."""
    if request.method == 'POST':
        form = YouthEventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            messages.success(request, f'Activité « {event.title} » créée.')
            return redirect('young:event_detail', pk=event.pk)
    else:
        form = YouthEventForm()

    return render(request, 'young/event_form.html', {
        'form': form,
        'title': 'Nouvelle activité',
    })


@login_required
@role_required(*YOUNG_ROLES)
def event_edit(request, pk):
    """Modifier une activité jeunesse."""
    event = get_object_or_404(YouthEvent, pk=pk)

    if request.method == 'POST':
        form = YouthEventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, f'Activité « {event.title} » modifiée.')
            return redirect('young:event_detail', pk=event.pk)
    else:
        form = YouthEventForm(instance=event)

    return render(request, 'young/event_form.html', {
        'form': form,
        'event': event,
        'title': f'Modifier {event.title}',
    })


# =============================================================================
# PRÉSENCES
# =============================================================================

@login_required
@role_required(*YOUNG_ROLES)
def take_attendance(request, event_pk):
    """
    Faire l'appel pour une activité jeunesse.
    Génère automatiquement les lignes de présence pour les jeunes actifs.
    """
    event = get_object_or_404(YouthEvent, pk=event_pk)
    active_members = YoungMember.objects.filter(is_active=True).select_related('group')

    # Créer les lignes de présence manquantes
    existing_ids = set(
        YouthAttendance.objects.filter(event=event).values_list('young_member_id', flat=True)
    )
    new_attendances = []
    for member in active_members:
        if member.pk not in existing_ids:
            new_attendances.append(YouthAttendance(
                event=event,
                young_member=member,
                status=YouthAttendance.Status.ABSENT,
            ))
    if new_attendances:
        YouthAttendance.objects.bulk_create(new_attendances)

    if request.method == 'POST':
        updated = 0
        for att in YouthAttendance.objects.filter(event=event):
            new_status = request.POST.get(f'status_{att.pk}')
            transported = request.POST.get(f'transported_{att.pk}') == 'on'

            if new_status and new_status in dict(YouthAttendance.Status.choices):
                att.status = new_status
                att.transported = transported
                att.recorded_by = request.user
                if new_status in ['present', 'retard'] and not att.check_in_time:
                    att.check_in_time = timezone.now().time()
                att.save()
                updated += 1

        messages.success(request, f'Appel enregistré ({updated} présences mises à jour).')
        return redirect('young:event_detail', pk=event.pk)

    attendances = YouthAttendance.objects.filter(
        event=event,
    ).select_related('young_member', 'young_member__group').order_by(
        'young_member__last_name', 'young_member__first_name',
    )

    context = {
        'event': event,
        'attendances': attendances,
        'status_choices': YouthAttendance.Status.choices,
    }
    return render(request, 'young/take_attendance.html', context)


@login_required
@role_required(*YOUNG_ROLES)
def update_attendance_status(request, attendance_pk):
    """Mise à jour HTMX d'un statut de présence."""
    attendance = get_object_or_404(YouthAttendance, pk=attendance_pk)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status and new_status in dict(YouthAttendance.Status.choices):
            attendance.status = new_status
            attendance.recorded_by = request.user
            if new_status in ['present', 'retard'] and not attendance.check_in_time:
                attendance.check_in_time = timezone.now().time()
            attendance.save()

    return render(request, 'young/partials/attendance_row.html', {
        'att': attendance,
        'status_choices': YouthAttendance.Status.choices,
    })
