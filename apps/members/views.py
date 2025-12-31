from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Member


@login_required
def member_list(request):
    """Liste des membres avec recherche et filtrage."""
    members = Member.objects.all()
    
    # Recherche
    search = request.GET.get('search', '')
    if search:
        members = members.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )
    
    # Filtrage par statut
    status = request.GET.get('status', '')
    if status:
        members = members.filter(status=status)
    
    # Pagination
    paginator = Paginator(members, 25)
    page = request.GET.get('page')
    members = paginator.get_page(page)
    
    context = {
        'members': members,
        'search': search,
        'status': status,
        'status_choices': Member.Status.choices,
    }
    
    if request.htmx:
        return render(request, 'members/partials/member_list.html', context)
    return render(request, 'members/member_list.html', context)


@login_required
def member_detail(request, pk):
    """Détail d'un membre."""
    member = get_object_or_404(Member, pk=pk)
    return render(request, 'members/member_detail.html', {'member': member})

