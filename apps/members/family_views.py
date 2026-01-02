"""
Vues pour la gestion des familles.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count

from apps.core.models import Family, Neighborhood, Site
from .models import Member


@login_required
def family_list(request):
    """Liste des familles."""
    families = Family.objects.annotate(
        member_count=Count('members')
    ).select_related('site', 'neighborhood', 'neighborhood__city').order_by('name')
    
    # Filtres
    site_id = request.GET.get('site')
    neighborhood_id = request.GET.get('neighborhood')
    search = request.GET.get('search')
    
    if site_id:
        families = families.filter(site_id=site_id)
    if neighborhood_id:
        families = families.filter(neighborhood_id=neighborhood_id)
    if search:
        families = families.filter(name__icontains=search)
    
    context = {
        'families': families,
        'sites': Site.objects.filter(is_active=True),
        'neighborhoods': Neighborhood.objects.filter(is_active=True).select_related('city'),
        'total_count': families.count(),
    }
    
    return render(request, 'members/family_list.html', context)


@login_required
def family_detail(request, pk):
    """Détail d'une famille."""
    family = get_object_or_404(
        Family.objects.select_related('site', 'neighborhood', 'neighborhood__city'),
        pk=pk
    )
    
    members = family.members.all().order_by('-family_role', 'last_name', 'first_name')
    
    context = {
        'family': family,
        'members': members,
    }
    
    return render(request, 'members/family_detail.html', context)


@login_required
def family_create(request):
    """Créer une nouvelle famille."""
    if request.method == 'POST':
        name = request.POST.get('name')
        site_id = request.POST.get('site')
        neighborhood_id = request.POST.get('neighborhood') or None
        address = request.POST.get('address', '')
        city = request.POST.get('city', '')
        postal_code = request.POST.get('postal_code', '')
        phone = request.POST.get('phone', '')
        email = request.POST.get('email', '')
        
        family = Family.objects.create(
            name=name,
            site_id=site_id if site_id else None,
            neighborhood_id=neighborhood_id,
            address=address,
            city=city,
            postal_code=postal_code,
            phone=phone,
            email=email,
        )
        
        messages.success(request, f"Famille '{name}' créée avec succès.")
        return redirect('members:family_detail', pk=family.pk)
    
    context = {
        'sites': Site.objects.filter(is_active=True),
        'neighborhoods': Neighborhood.objects.filter(is_active=True).select_related('city'),
    }
    
    return render(request, 'members/family_create.html', context)


@login_required
def family_edit(request, pk):
    """Modifier une famille."""
    family = get_object_or_404(Family, pk=pk)
    
    if request.method == 'POST':
        family.name = request.POST.get('name')
        family.site_id = request.POST.get('site') or None
        family.neighborhood_id = request.POST.get('neighborhood') or None
        family.address = request.POST.get('address', '')
        family.city = request.POST.get('city', '')
        family.postal_code = request.POST.get('postal_code', '')
        family.phone = request.POST.get('phone', '')
        family.email = request.POST.get('email', '')
        family.latitude = request.POST.get('latitude') or None
        family.longitude = request.POST.get('longitude') or None
        family.notes = request.POST.get('notes', '')
        family.save()
        
        messages.success(request, f"Famille '{family.name}' mise à jour.")
        return redirect('members:family_detail', pk=pk)
    
    context = {
        'family': family,
        'sites': Site.objects.filter(is_active=True),
        'neighborhoods': Neighborhood.objects.filter(is_active=True).select_related('city'),
    }
    
    return render(request, 'members/family_edit.html', context)


@login_required
def family_add_member(request, pk):
    """Ajouter un membre à une famille."""
    family = get_object_or_404(Family, pk=pk)
    
    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        family_role = request.POST.get('family_role', '')
        
        member = get_object_or_404(Member, pk=member_id)
        member.family = family
        member.family_role = family_role
        member.save()
        
        messages.success(request, f"{member.full_name} ajouté à la famille {family.name}.")
        return redirect('members:family_detail', pk=pk)
    
    # Membres sans famille
    available_members = Member.objects.filter(
        family__isnull=True,
        status='actif'
    ).order_by('last_name', 'first_name')
    
    context = {
        'family': family,
        'available_members': available_members,
        'family_roles': [
            ('HEAD', 'Chef de famille'),
            ('SPOUSE', 'Conjoint(e)'),
            ('CHILD', 'Enfant'),
            ('PARENT', 'Parent'),
            ('OTHER', 'Autre'),
        ],
    }
    
    return render(request, 'members/family_add_member.html', context)
