"""
Vues admin personnalisées pour les membres.
Inclut une carte interactive des membres par quartier/famille.
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count, Q

from .models import Member
from .geocoding import geocode_address
from apps.core.models import Site, Neighborhood, Family


def members_map_view(request):
    """Vue carte des membres (accessible aux utilisateurs connectés)."""
    
    # Filtres
    site_id = request.GET.get('site')
    neighborhood_id = request.GET.get('neighborhood')
    status = request.GET.get('status')
    
    # Sites pour le filtre
    sites = Site.objects.filter(is_active=True)
    neighborhoods = Neighborhood.objects.filter(is_active=True).select_related('city')
    
    context = {
        'title': 'Carte des membres',
        'sites': sites,
        'neighborhoods': neighborhoods,
        'selected_site': site_id,
        'selected_neighborhood': neighborhood_id,
        'selected_status': status,
        'status_choices': Member.Status.choices if hasattr(Member, 'Status') else [],
    }
    
    # Utiliser le template admin ou app selon le chemin
    if '/admin/' in request.path:
        return render(request, 'admin/members/members_map.html', context)
    return render(request, 'members/members_map.html', context)


@login_required
def members_map_data(request):
    """API JSON pour les données de la carte avec géocodage."""
    
    # Filtres
    site_id = request.GET.get('site')
    status = request.GET.get('status')
    city_filter = request.GET.get('city')
    
    # Données des sites (églises)
    sites_data = []
    sites_qs = Site.objects.filter(
        is_active=True,
        latitude__isnull=False,
        longitude__isnull=False
    )
    
    for site in sites_qs:
        member_count = Member.objects.filter(site=site).count()
        sites_data.append({
            'type': 'site',
            'id': site.id,
            'name': site.name,
            'lat': float(site.latitude),
            'lng': float(site.longitude),
            'address': site.address,
            'city': site.city,
            'member_count': member_count,
        })
    
    # Données des membres avec adresse
    members_data = []
    members_qs = Member.objects.filter(
        Q(address__isnull=False) & ~Q(address='')
    ).select_related('site', 'family')
    
    if site_id:
        members_qs = members_qs.filter(site_id=site_id)
    if status:
        members_qs = members_qs.filter(status=status)
    if city_filter:
        members_qs = members_qs.filter(city__icontains=city_filter)
    
    # Limiter pour éviter trop de requêtes de géocodage
    members_qs = members_qs[:100]
    
    # Cache pour éviter de géocoder plusieurs fois la même adresse
    geocode_cache = {}
    
    for member in members_qs:
        # Créer une clé de cache basée sur l'adresse
        cache_key = f"{member.address}|{member.city}|{member.postal_code}"
        
        if cache_key in geocode_cache:
            coords = geocode_cache[cache_key]
        else:
            coords = geocode_address(
                address=member.address,
                city=member.city,
                postal_code=member.postal_code
            )
            geocode_cache[cache_key] = coords
        
        if coords:
            members_data.append({
                'type': 'member',
                'id': member.id,
                'name': member.full_name,
                'lat': coords[0],
                'lng': coords[1],
                'address': member.address,
                'city': member.city,
                'phone': member.phone or '',
                'status': member.status,
                'site': member.site.name if member.site else '',
                'family': member.family.name if member.family else '',
            })
    
    # Statistiques
    total_members = Member.objects.count()
    members_with_address = Member.objects.filter(
        Q(address__isnull=False) & ~Q(address='')
    ).count()
    members_geocoded = len(members_data)
    
    # Villes uniques pour le filtre
    cities = Member.objects.exclude(
        Q(city__isnull=True) | Q(city='')
    ).values_list('city', flat=True).distinct()
    
    return JsonResponse({
        'sites': sites_data,
        'members': members_data,
        'cities': list(cities),
        'stats': {
            'total_members': total_members,
            'members_with_address': members_with_address,
            'members_geocoded': members_geocoded,
        }
    })
