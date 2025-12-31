from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Member


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
    members_qs = members_qs.order_by('last_name', 'first_name')
    
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
    }
    
    if request.htmx:
        return render(request, 'members/partials/member_list.html', context)
    return render(request, 'members/member_list.html', context)


@login_required
def member_detail(request, pk):
    """Détail d'un membre."""
    member = get_object_or_404(Member, pk=pk)
    return render(request, 'members/member_detail.html', {'member': member})
