from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.core import signing
from urllib.parse import quote_plus
from apps.core.permissions import role_required
from .models import Campaign, Donation
from .forms import CampaignForm, DonationForm
import logging

logger = logging.getLogger(__name__)



@login_required
def campaign_list(request):
    """Liste des campagnes."""
    campaigns = Campaign.objects.all()
    
    # Filtrer par statut actif
    active_only = request.GET.get('active', 'true') == 'true'
    if active_only:
        campaigns = campaigns.filter(is_active=True)
    
    paginator = Paginator(campaigns, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    
    context = {
        'campaigns': page_obj,
        'page_obj': page_obj,
        'active_only': active_only,
    }
    return render(request, 'campaigns/campaign_list.html', context)


@login_required
def campaign_detail(request, pk):
    """Détail d'une campagne."""
    campaign = get_object_or_404(Campaign, pk=pk)
    donations = campaign.donations.all()[:20]

    campaign_token = signing.dumps({'campaign_id': campaign.pk}, salt='campaign-donation')
    donation_path = f"{reverse('public:donation')}?c={campaign_token}"
    public_donation_url = request.build_absolute_uri(donation_path)
    qr_code_url = f"https://quickchart.io/qr?size=280&text={quote_plus(public_donation_url)}"
    
    context = {
        'campaign': campaign,
        'donations': donations,
        'public_donation_url': public_donation_url,
        'qr_code_url': qr_code_url,
    }
    return render(request, 'campaigns/campaign_detail.html', context)


@login_required
@role_required('admin', 'finance')
def campaign_create(request):
    """Créer une nouvelle campagne."""
    if request.method == 'POST':
        form = CampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save()
            messages.success(request, f'Campagne "{campaign.name}" créée avec succès.')
            return redirect('campaigns:detail', pk=campaign.pk)
    else:
        form = CampaignForm()
    
    context = {
        'form': form,
        'title': 'Nouvelle campagne',
        'submit_text': 'Créer la campagne'
    }
    return render(request, 'campaigns/campaign_form.html', context)


@login_required
@role_required('admin', 'finance')
def campaign_update(request, pk):
    """Modifier une campagne existante."""
    campaign = get_object_or_404(Campaign, pk=pk)
    
    if request.method == 'POST':
        form = CampaignForm(request.POST, instance=campaign)
        if form.is_valid():
            campaign = form.save()
            messages.success(request, f'Campagne "{campaign.name}" modifiée avec succès.')
            return redirect('campaigns:detail', pk=campaign.pk)
    else:
        form = CampaignForm(instance=campaign)
    
    context = {
        'form': form,
        'campaign': campaign,
        'title': f'Modifier "{campaign.name}"',
        'submit_text': 'Enregistrer les modifications'
    }
    return render(request, 'campaigns/campaign_form.html', context)


@login_required
@role_required('admin', 'finance', 'secretariat')
def campaign_donate(request, pk=None):
    """Enregistrer un don pour une campagne."""
    campaign = None
    if pk:
        campaign = get_object_or_404(Campaign, pk=pk, is_active=True)
    
    if request.method == 'POST':
        form = DonationForm(request.POST, campaign_id=pk)
        if form.is_valid():
            donation = form.save()
            
            # Vérifier si l'objectif est atteint pour la notification
            campaign = donation.campaign
            was_goal_reached_before = (campaign.collected_amount - donation.amount) >= campaign.goal_amount
            is_goal_reached_now = campaign.collected_amount >= campaign.goal_amount
            
            messages.success(
                request, 
                f'Don de {donation.amount}€ enregistré avec succès pour "{campaign.name}".'
            )
            
            # Notification spéciale si objectif atteint pour la première fois
            if is_goal_reached_now and not was_goal_reached_before:
                messages.success(
                    request,
                    f'🎉 Félicitations ! L\'objectif de la campagne "{campaign.name}" a été atteint !',
                    extra_tags='goal-reached'
                )
            
            return redirect('campaigns:detail', pk=campaign.pk)
    else:
        form = DonationForm(campaign_id=pk)
    
    context = {
        'form': form,
        'campaign': campaign,
        'title': f'Nouveau don{" pour " + campaign.name if campaign else ""}',
        'submit_text': 'Enregistrer le don'
    }
    return render(request, 'campaigns/donation_form.html', context)


@login_required
@require_http_methods(["GET"])
def campaign_progress_api(request, pk):
    """API pour récupérer la progression d'une campagne (pour les mises à jour en temps réel)."""
    campaign = get_object_or_404(Campaign, pk=pk)
    
    data = {
        'collected_amount': float(campaign.collected_amount),
        'goal_amount': float(campaign.goal_amount),
        'progress_percentage': campaign.progress_percentage,
        'remaining_amount': float(campaign.remaining_amount),
        'status_color': campaign.status_color,
        'goal_reached': campaign.collected_amount >= campaign.goal_amount
    }
    
    return JsonResponse(data)


@login_required
@role_required('admin', 'finance')
def campaign_delete(request, pk):
    """Supprimer une campagne (soft delete)."""
    campaign = get_object_or_404(Campaign, pk=pk)
    
    # Vérifier l'activité
    donations_count = campaign.donations.count()
    
    if request.method == 'POST':
        campaign.is_active = False
        campaign.save()
        messages.success(request, f'La campagne "{campaign.name}" a été supprimée (archivée) avec succès.')
        return redirect('campaigns:list')
    
    context = {
        'campaign': campaign,
        'donations_count': donations_count,
    }
    return render(request, 'campaigns/campaign_delete_confirm.html', context)


@login_required
@role_required('admin', 'finance')
def donation_cancel(request, pk):
    """Annuler un don."""
    donation = get_object_or_404(Donation, pk=pk)
    campaign = donation.campaign
    
    if request.method == 'POST':
        if not donation.is_cancelled:
            donation.is_cancelled = True
            donation.save()
            messages.success(request, f'Le don de {donation.amount}€ a été annulé avec succès.')
        else:
            donation.is_cancelled = False
            donation.save()
            messages.success(request, f'Le don de {donation.amount}€ a été réactivé avec succès.')
            
        return redirect('campaigns:detail', pk=campaign.pk)
    
    context = {
        'donation': donation,
        'campaign': campaign,
    }
    return render(request, 'campaigns/donation_cancel_confirm.html', context)

