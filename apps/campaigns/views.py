from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Campaign


@login_required
def campaign_list(request):
    """Liste des campagnes."""
    campaigns = Campaign.objects.all()
    
    # Filtrer par statut actif
    active_only = request.GET.get('active', 'true') == 'true'
    if active_only:
        campaigns = campaigns.filter(is_active=True)
    
    context = {
        'campaigns': campaigns,
        'active_only': active_only,
    }
    return render(request, 'campaigns/campaign_list.html', context)


@login_required
def campaign_detail(request, pk):
    """Détail d'une campagne."""
    campaign = get_object_or_404(Campaign, pk=pk)
    donations = campaign.donations.all()[:20]
    
    context = {
        'campaign': campaign,
        'donations': donations,
    }
    return render(request, 'campaigns/campaign_detail.html', context)

