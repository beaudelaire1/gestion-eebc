"""
Vues pour les dons en ligne via Stripe.
"""

import json
from decimal import Decimal
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.conf import settings

from .stripe_service import stripe_service
from .models import OnlineDonation


class DonationPageView(TemplateView):
    """Page de don en ligne."""
    template_name = 'finance/donation_page.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stripe_public_key'] = stripe_service.public_key
        context['stripe_configured'] = stripe_service.is_configured
        
        # Sites disponibles
        from apps.core.models import Site
        context['sites'] = Site.objects.filter(is_active=True)
        
        return context


class CreateDonationSessionView(View):
    """Crée une session de paiement Stripe."""
    
    def post(self, request):
        if not stripe_service.is_configured:
            return JsonResponse({
                'error': 'Le paiement en ligne n\'est pas configuré'
            }, status=400)
        
        try:
            data = json.loads(request.body)
            
            amount = Decimal(data.get('amount', 0))
            if amount < 1:
                return JsonResponse({
                    'error': 'Le montant minimum est de 1€'
                }, status=400)
            
            donation_type = data.get('type', 'don')
            donor_email = data.get('email', '')
            site_id = data.get('site_id')
            is_recurring = data.get('recurring', False)
            
            # Membre connecté ?
            member_id = None
            if request.user.is_authenticated:
                if hasattr(request.user, 'member_profile'):
                    member_id = request.user.member_profile.id
            
            # URLs de retour
            success_url = request.build_absolute_uri('/don/succes/?session_id={CHECKOUT_SESSION_ID}')
            cancel_url = request.build_absolute_uri('/don/annule/')
            
            if is_recurring:
                result = stripe_service.create_recurring_donation(
                    amount=amount,
                    donation_type=donation_type,
                    interval=data.get('interval', 'month'),
                    donor_email=donor_email,
                    member_id=member_id,
                    site_id=site_id,
                    success_url=success_url,
                    cancel_url=cancel_url,
                )
            else:
                result = stripe_service.create_donation_session(
                    amount=amount,
                    donation_type=donation_type,
                    donor_email=donor_email,
                    member_id=member_id,
                    site_id=site_id,
                    success_url=success_url,
                    cancel_url=cancel_url,
                )
            
            return JsonResponse(result)
        
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=400)


class DonationSuccessView(TemplateView):
    """Page de succès après un don."""
    template_name = 'finance/donation_success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        session_id = self.request.GET.get('session_id')
        if session_id:
            try:
                donation = OnlineDonation.objects.get(stripe_session_id=session_id)
                context['donation'] = donation
            except OnlineDonation.DoesNotExist:
                pass
        
        return context


class DonationCancelView(TemplateView):
    """Page d'annulation de don."""
    template_name = 'finance/donation_cancel.html'


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    """Endpoint pour les webhooks Stripe."""
    
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        
        try:
            result = stripe_service.handle_webhook(payload, sig_header)
            return JsonResponse(result)
        
        except ValueError as e:
            return HttpResponse(status=400)
        
        except Exception as e:
            return HttpResponse(status=400)
