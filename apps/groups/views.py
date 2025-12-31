from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Group, GroupMeeting


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
    recent_meetings = group.meetings.filter(is_cancelled=False)[:5]
    
    context = {
        'group': group,
        'members': members,
        'recent_meetings': recent_meetings,
    }
    return render(request, 'groups/group_detail.html', context)

