"""
Vues pour la confirmation des rôles de culte.

Ces vues permettent aux membres de confirmer ou refuser leur participation
via un lien unique (token) sans avoir besoin de se connecter.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from django.utils import timezone

from .models import RoleAssignment, ScheduledService, MonthlySchedule
from apps.members.models import Member
from apps.core.permissions import role_required


def confirm_role(request, token):
    """
    Page de confirmation d'un rôle (accessible sans connexion).
    """
    assignment = get_object_or_404(RoleAssignment, token=token)
    
    # Vérifier si déjà traité
    if assignment.status != RoleAssignment.Status.PENDING:
        return render(request, 'worship/confirmation/already_responded.html', {
            'assignment': assignment,
        })
    
    # Vérifier si expiré
    if assignment.is_expired:
        assignment.status = RoleAssignment.Status.EXPIRED
        assignment.save()
        return render(request, 'worship/confirmation/expired.html', {
            'assignment': assignment,
        })
    
    if request.method == 'POST':
        assignment.accept()
        return render(request, 'worship/confirmation/confirmed.html', {
            'assignment': assignment,
        })
    
    return render(request, 'worship/confirmation/confirm.html', {
        'assignment': assignment,
        'service': assignment.scheduled_service,
        'schedule': assignment.scheduled_service.schedule,
    })


def decline_role(request, token):
    """
    Page de refus d'un rôle (accessible sans connexion).
    """
    assignment = get_object_or_404(RoleAssignment, token=token)
    
    # Vérifier si déjà traité
    if assignment.status != RoleAssignment.Status.PENDING:
        return render(request, 'worship/confirmation/already_responded.html', {
            'assignment': assignment,
        })
    
    # Vérifier si expiré
    if assignment.is_expired:
        assignment.status = RoleAssignment.Status.EXPIRED
        assignment.save()
        return render(request, 'worship/confirmation/expired.html', {
            'assignment': assignment,
        })
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        replacement_id = request.POST.get('suggested_replacement')
        
        suggested_replacement = None
        if replacement_id:
            try:
                suggested_replacement = Member.objects.get(pk=replacement_id)
            except Member.DoesNotExist:
                pass
        
        assignment.decline(reason=reason, suggested_replacement=suggested_replacement)
        
        return render(request, 'worship/confirmation/declined.html', {
            'assignment': assignment,
        })
    
    # Suggérer des remplaçants potentiels
    potential_replacements = Member.objects.filter(
        status='actif'
    ).exclude(pk=assignment.member.pk).order_by('last_name', 'first_name')[:20]
    
    return render(request, 'worship/confirmation/decline.html', {
        'assignment': assignment,
        'service': assignment.scheduled_service,
        'schedule': assignment.scheduled_service.schedule,
        'potential_replacements': potential_replacements,
    })


@login_required
@role_required('admin', 'responsable_groupe')
def role_assignments_list(request, service_pk):
    """
    Liste des assignations de rôles pour un culte (admin).
    """
    service = get_object_or_404(ScheduledService, pk=service_pk)
    assignments = service.role_assignments.select_related('member').order_by('role')
    
    context = {
        'service': service,
        'schedule': service.schedule,
        'assignments': assignments,
        'pending_count': assignments.filter(status='pending').count(),
        'accepted_count': assignments.filter(status='accepted').count(),
        'declined_count': assignments.filter(status='declined').count(),
    }
    
    return render(request, 'worship/role_assignments.html', context)


@login_required
@role_required('admin', 'responsable_groupe')
def create_role_assignment(request, service_pk):
    """
    Créer une assignation de rôle et envoyer la notification.
    """
    service = get_object_or_404(ScheduledService, pk=service_pk)
    
    if request.method == 'POST':
        member_id = request.POST.get('member')
        role = request.POST.get('role')
        send_notification = request.POST.get('send_notification') == 'on'
        
        member = get_object_or_404(Member, pk=member_id)
        
        # Créer l'assignation
        assignment, created = RoleAssignment.objects.get_or_create(
            scheduled_service=service,
            member=member,
            role=role,
            defaults={'status': 'pending'}
        )
        
        if created:
            if send_notification:
                # Envoyer la notification
                base_url = request.build_absolute_uri('/').rstrip('/')
                assignment.send_notification(base_url=base_url)
                messages.success(request, f"Assignation créée et notification envoyée à {member.full_name}")
            else:
                messages.success(request, f"Assignation créée pour {member.full_name}")
        else:
            messages.warning(request, f"{member.full_name} est déjà assigné(e) à ce rôle")
        
        return redirect('worship:role_assignments', service_pk=service_pk)
    
    members = Member.objects.filter(status='actif').order_by('last_name', 'first_name')
    
    context = {
        'service': service,
        'schedule': service.schedule,
        'members': members,
        'role_choices': RoleAssignment.RoleType.choices,
    }
    
    return render(request, 'worship/create_role_assignment.html', context)


@login_required
@role_required('admin', 'responsable_groupe')
def send_assignment_notification(request, pk):
    """
    Envoyer/renvoyer la notification pour une assignation.
    """
    assignment = get_object_or_404(RoleAssignment, pk=pk)
    
    base_url = request.build_absolute_uri('/').rstrip('/')
    assignment.send_notification(base_url=base_url)
    
    messages.success(request, f"Notification envoyée à {assignment.member.full_name}")
    return redirect('worship:role_assignments', service_pk=assignment.scheduled_service.pk)


@login_required
@role_required('admin', 'responsable_groupe')
def send_all_notifications(request, service_pk):
    """
    Envoyer les notifications à tous les membres en attente.
    """
    service = get_object_or_404(ScheduledService, pk=service_pk)
    
    pending_assignments = service.role_assignments.filter(
        status='pending',
        notified_at__isnull=True
    )
    
    base_url = request.build_absolute_uri('/').rstrip('/')
    sent_count = 0
    
    for assignment in pending_assignments:
        try:
            assignment.send_notification(base_url=base_url)
            sent_count += 1
        except Exception as e:
            messages.error(request, f"Erreur pour {assignment.member.full_name}: {e}")
    
    if sent_count:
        messages.success(request, f"{sent_count} notification(s) envoyée(s)")
    else:
        messages.info(request, "Aucune notification à envoyer")
    
    return redirect('worship:role_assignments', service_pk=service_pk)
