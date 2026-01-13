from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from apps.core.permissions import role_required
from .models import Group, GroupMeeting
from .forms import GroupForm, GroupMembersForm, GroupMeetingForm, GroupMeetingAttendanceForm
from .services import GroupService, GroupMeetingService


@login_required
def group_list(request):
    """Liste des groupes."""
    groups = Group.objects.filter(is_active=True).select_related('leader')
    
    group_type = request.GET.get('type')
    if group_type:
        groups = groups.filter(group_type=group_type)
    
    context = {
        'groups': groups,
        'group_types': Group.GroupType.choices,
    }
    return render(request, 'groups/group_list.html', context)


@login_required
def group_detail(request, pk):
    """Détail d'un groupe."""
    group = get_object_or_404(Group, pk=pk)
    members = group.members.all()
    recent_meetings = GroupMeetingService.get_recent_meetings(group)
    
    # Statistiques de présence
    meetings_stats = GroupService.get_group_statistics(group)
    
    context = {
        'group': group,
        'members': members,
        'recent_meetings': recent_meetings,
        'meetings_stats': meetings_stats,
    }
    return render(request, 'groups/group_detail.html', context)


@login_required
@role_required('admin', 'secretariat', 'responsable_groupe')
def group_create(request):
    """Créer un nouveau groupe."""
    if request.method == 'POST':
        form = GroupForm(request.POST, request.FILES)
        if form.is_valid():
            group = form.save()
            messages.success(request, f'Le groupe "{group.name}" a été créé avec succès.')
            return redirect('groups:detail', pk=group.pk)
    else:
        form = GroupForm()
    
    context = {
        'form': form,
        'title': 'Créer un groupe',
        'submit_text': 'Créer le groupe'
    }
    return render(request, 'groups/group_form.html', context)


@login_required
@role_required('admin', 'secretariat', 'responsable_groupe')
def group_update(request, pk):
    """Modifier un groupe."""
    group = get_object_or_404(Group, pk=pk)
    
    # Vérifier si l'utilisateur peut modifier ce groupe
    if (request.user.role == 'responsable_groupe' and 
        group.leader != request.user and 
        request.user.role != 'admin'):
        messages.error(request, "Vous ne pouvez modifier que vos propres groupes.")
        return redirect('groups:detail', pk=pk)
    
    if request.method == 'POST':
        form = GroupForm(request.POST, request.FILES, instance=group)
        if form.is_valid():
            group = form.save()
            messages.success(request, f'Le groupe "{group.name}" a été modifié avec succès.')
            return redirect('groups:detail', pk=group.pk)
    else:
        form = GroupForm(instance=group)
    
    context = {
        'form': form,
        'group': group,
        'title': f'Modifier {group.name}',
        'submit_text': 'Enregistrer les modifications'
    }
    return render(request, 'groups/group_form.html', context)


@login_required
@role_required('admin', 'secretariat', 'responsable_groupe')
def group_members_manage(request, pk):
    """Gérer les membres d'un groupe."""
    group = get_object_or_404(Group, pk=pk)
    
    # Vérifier si l'utilisateur peut gérer ce groupe
    if (request.user.role == 'responsable_groupe' and 
        group.leader != request.user and 
        request.user.role != 'admin'):
        messages.error(request, "Vous ne pouvez gérer que vos propres groupes.")
        return redirect('groups:detail', pk=pk)
    
    if request.method == 'POST':
        form = GroupMembersForm(request.POST, group=group)
        if form.is_valid():
            # Mettre à jour les membres du groupe
            group.members.set(form.cleaned_data['members'])
            messages.success(request, f'Les membres du groupe "{group.name}" ont été mis à jour.')
            return redirect('groups:detail', pk=group.pk)
    else:
        form = GroupMembersForm(group=group)
    
    context = {
        'form': form,
        'group': group,
        'title': f'Gérer les membres - {group.name}'
    }
    return render(request, 'groups/group_members_manage.html', context)


@login_required
@role_required('admin', 'secretariat', 'responsable_groupe')
def group_meeting_create(request, group_pk):
    """Planifier une nouvelle réunion."""
    group = get_object_or_404(Group, pk=group_pk)
    
    # Vérifier si l'utilisateur peut gérer ce groupe
    if (request.user.role == 'responsable_groupe' and 
        group.leader != request.user and 
        request.user.role != 'admin'):
        messages.error(request, "Vous ne pouvez gérer que vos propres groupes.")
        return redirect('groups:detail', pk=group_pk)
    
    if request.method == 'POST':
        form = GroupMeetingForm(request.POST, group=group)
        if form.is_valid():
            meeting = form.save(commit=False)
            meeting.group = group
            meeting.save()
            messages.success(request, 'La réunion a été planifiée avec succès.')
            return redirect('groups:detail', pk=group.pk)
    else:
        form = GroupMeetingForm(group=group)
    
    context = {
        'form': form,
        'group': group,
        'title': f'Planifier une réunion - {group.name}',
        'submit_text': 'Planifier la réunion'
    }
    return render(request, 'groups/meeting_form.html', context)


@login_required
@role_required('admin', 'secretariat', 'responsable_groupe')
def group_meeting_update(request, group_pk, meeting_pk):
    """Modifier une réunion."""
    group = get_object_or_404(Group, pk=group_pk)
    meeting = get_object_or_404(GroupMeeting, pk=meeting_pk, group=group)
    
    # Vérifier si l'utilisateur peut gérer ce groupe
    if (request.user.role == 'responsable_groupe' and 
        group.leader != request.user and 
        request.user.role != 'admin'):
        messages.error(request, "Vous ne pouvez gérer que vos propres groupes.")
        return redirect('groups:detail', pk=group_pk)
    
    if request.method == 'POST':
        form = GroupMeetingAttendanceForm(request.POST, instance=meeting)
        if form.is_valid():
            meeting = form.save()
            messages.success(request, 'La réunion a été mise à jour avec succès.')
            return redirect('groups:detail', pk=group.pk)
    else:
        form = GroupMeetingAttendanceForm(instance=meeting)
    
    context = {
        'form': form,
        'group': group,
        'meeting': meeting,
        'title': f'Modifier la réunion - {group.name}',
        'submit_text': 'Enregistrer les modifications'
    }
    return render(request, 'groups/meeting_form.html', context)


@login_required
def group_statistics(request, pk):
    """Statistiques de présence d'un groupe."""
    group = get_object_or_404(Group, pk=pk)
    
    # Utiliser le service pour obtenir les données
    chart_data = GroupService.get_attendance_chart_data(group)
    stats = GroupService.get_group_statistics(group)
    
    context = {
        'group': group,
        'chart_data': chart_data,
        'stats': stats,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(context)
    
    return render(request, 'groups/group_statistics.html', context)


@login_required
@role_required('admin', 'secretariat', 'responsable_groupe')
def group_generate_meetings(request, pk):
    """Générer des réunions récurrentes pour un groupe."""
    group = get_object_or_404(Group, pk=pk)
    
    # Vérifier si l'utilisateur peut gérer ce groupe
    if (request.user.role == 'responsable_groupe' and 
        group.leader != request.user and 
        request.user.role != 'admin'):
        messages.error(request, "Vous ne pouvez gérer que vos propres groupes.")
        return redirect('groups:detail', pk=pk)
    
    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            if start_date >= end_date:
                messages.error(request, "La date de fin doit être postérieure à la date de début.")
                return redirect('groups:detail', pk=pk)
            
            # Générer les réunions
            meetings = GroupMeetingService.generate_recurring_meetings(group, start_date, end_date)
            
            if meetings:
                created_meetings = GroupMeetingService.bulk_create_meetings(meetings)
                messages.success(request, f"{len(created_meetings)} réunions ont été planifiées avec succès.")
            else:
                messages.warning(request, "Aucune nouvelle réunion n'a été créée. Vérifiez les paramètres du groupe.")
            
        except ValueError:
            messages.error(request, "Format de date invalide.")
        
        return redirect('groups:detail', pk=pk)
    
    # GET request - afficher le formulaire
    context = {
        'group': group,
        'today': timezone.now().date(),
        'three_months_later': timezone.now().date() + timedelta(days=90)
    }
    return render(request, 'groups/generate_meetings.html', context)


@login_required
def groups_dashboard(request):
    """Dashboard des statistiques de tous les groupes."""
    groups = Group.objects.filter(is_active=True).select_related('leader')
    
    # Filtrer par responsable si nécessaire
    if request.user.role == 'responsable_groupe':
        groups = groups.filter(leader=request.user)
    
    # Calculer les statistiques pour chaque groupe
    groups_stats = []
    for group in groups:
        stats = GroupService.get_group_statistics(group, months=3)  # 3 derniers mois
        upcoming_meetings = GroupMeetingService.get_upcoming_meetings(group, days=30)
        
        groups_stats.append({
            'group': group,
            'stats': stats,
            'upcoming_meetings_count': upcoming_meetings.count(),
            'next_meeting': upcoming_meetings.first()
        })
    
    # Statistiques globales
    total_groups = groups.count()
    total_members = sum(group.member_count for group in groups)
    
    # Réunions cette semaine
    week_start = timezone.now().date()
    week_end = week_start + timedelta(days=7)
    meetings_this_week = GroupMeeting.objects.filter(
        group__in=groups,
        date__gte=week_start,
        date__lt=week_end,
        is_cancelled=False
    ).count()
    
    context = {
        'groups_stats': groups_stats,
        'total_groups': total_groups,
        'total_members': total_members,
        'meetings_this_week': meetings_this_week,
    }
    
    return render(request, 'groups/dashboard.html', context)


# =============================================================================
# OPÉRATIONS DE SUPPRESSION MANQUANTES
# =============================================================================

@login_required
@role_required('admin', 'secretariat', 'responsable_groupe')
def group_delete(request, pk):
    """Supprimer un groupe (soft delete)."""
    group = get_object_or_404(Group, pk=pk)
    
    # Vérifier si l'utilisateur peut supprimer ce groupe
    if (request.user.role == 'responsable_groupe' and 
        group.leader != request.user and 
        request.user.role != 'admin'):
        messages.error(request, "Vous ne pouvez supprimer que vos propres groupes.")
        return redirect('groups:detail', pk=pk)
    
    # Vérifier s'il y a des réunions liées
    meetings_count = group.meetings.count()
    future_meetings_count = group.meetings.filter(
        date__gte=timezone.now().date(),
        is_cancelled=False
    ).count()
    
    if request.method == 'POST':
        group_name = group.name
        
        # Soft delete - marquer comme inactif
        group.is_active = False
        group.save()
        
        # Optionnellement annuler les réunions futures
        if request.POST.get('cancel_future_meetings') == 'on':
            future_meetings = group.meetings.filter(
                date__gte=timezone.now().date(),
                is_cancelled=False
            )
            future_meetings.update(is_cancelled=True)
            messages.info(request, f'{future_meetings_count} réunion(s) future(s) annulée(s).')
        
        messages.success(request, f'Groupe "{group_name}" supprimé avec succès.')
        return redirect('groups:list')
    
    context = {
        'group': group,
        'meetings_count': meetings_count,
        'future_meetings_count': future_meetings_count,
    }
    return render(request, 'groups/group_delete_confirm.html', context)


@login_required
@role_required('admin', 'secretariat', 'responsable_groupe')
def meeting_delete(request, group_pk, meeting_pk):
    """Supprimer une réunion."""
    group = get_object_or_404(Group, pk=group_pk)
    meeting = get_object_or_404(GroupMeeting, pk=meeting_pk, group=group)
    
    # Vérifier si l'utilisateur peut supprimer cette réunion
    if (request.user.role == 'responsable_groupe' and 
        group.leader != request.user and 
        request.user.role != 'admin'):
        messages.error(request, "Vous ne pouvez supprimer que les réunions de vos propres groupes.")
        return redirect('groups:detail', pk=group_pk)
    
    if request.method == 'POST':
        meeting_date = meeting.date
        meeting.delete()
        
        messages.success(request, f'Réunion du {meeting_date.strftime("%d/%m/%Y")} supprimée avec succès.')
        return redirect('groups:detail', pk=group.pk)
    
    context = {
        'group': group,
        'meeting': meeting,
    }
    return render(request, 'groups/meeting_delete_confirm.html', context)

