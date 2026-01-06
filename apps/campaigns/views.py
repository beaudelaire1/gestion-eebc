from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from apps.core.permissions import role_required
from .models import Campaign, Donation
from .forms import CampaignForm, DonationForm


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

