"""
Vues pour les dons en ligne via Stripe.
"""

import json
import logging
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.conf import settings
from django.core import signing
from apps.core.models import SiteSettings, PageContent

from .stripe_service import stripe_service
from .models import OnlineDonation
from apps.core.utils.turnstile import validate_turnstile, get_client_ip

logger = logging.getLogger(__name__)


class DonationPageView(TemplateView):
    """Page de don en ligne."""
    template_name = 'finance/donation_page.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stripe_public_key'] = stripe_service.public_key
        context['stripe_configured'] = stripe_service.is_configured
        context['settings'] = SiteSettings.get_settings()
        context['menu_pages'] = PageContent.objects.filter(
            is_published=True,
            show_in_menu=True
        ).order_by('menu_order')
        context['turnstile_site_key'] = getattr(settings, 'TURNSTILE_SITE_KEY', '')
        
        # Sites disponibles
        from apps.core.models import Site
        context['sites'] = Site.objects.filter(is_active=True)

        # Campagne sélectionnée via token signé (partage mobile sécurisé)
        token = self.request.GET.get('c')
        selected_campaign = None
        if token:
            try:
                payload = signing.loads(token, salt='campaign-donation', max_age=60 * 60 * 24 * 365)
                campaign_id = payload.get('campaign_id')
                if campaign_id:
                    from apps.campaigns.models import Campaign
                    selected_campaign = Campaign.objects.filter(pk=campaign_id, is_active=True).first()
            except signing.BadSignature:
                selected_campaign = None

        context['selected_campaign'] = selected_campaign
        context['campaign_token'] = token if selected_campaign else ''
        
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
            
            # Valider le CAPTCHA Turnstile
            turnstile_token = data.get('turnstile_token')
            ip_address = get_client_ip(request)
            is_valid, captcha_error = validate_turnstile(turnstile_token, ip_address)
            if not is_valid:
                return JsonResponse({
                    'error': captcha_error or 'Vérification de sécurité échouée.'
                }, status=403)
            
            amount = Decimal(data.get('amount', 0))
            if amount < 1:
                return JsonResponse({
                    'error': 'Le montant minimum est de 1€'
                }, status=400)
            
            donation_type = data.get('type', 'don')
            donor_email = data.get('email', '')
            donor_name = data.get('donor_name', '')
            site_id = data.get('site_id')
            is_recurring = data.get('recurring', False)
            campaign_id = None

            campaign_token = data.get('campaign_token')
            if campaign_token:
                try:
                    payload = signing.loads(campaign_token, salt='campaign-donation', max_age=60 * 60 * 24 * 365)
                    campaign_id = payload.get('campaign_id')
                    if campaign_id:
                        from apps.campaigns.models import Campaign
                        if not Campaign.objects.filter(pk=campaign_id, is_active=True).exists():
                            return JsonResponse({'error': 'Campagne invalide ou inactive.'}, status=400)
                except signing.BadSignature:
                    return JsonResponse({'error': 'Lien de campagne invalide ou expiré.'}, status=400)
            
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
                    campaign_id=campaign_id,
                    success_url=success_url,
                    cancel_url=cancel_url,
                )
            else:
                result = stripe_service.create_donation_session(
                    amount=amount,
                    donation_type=donation_type,
                    donor_email=donor_email,
                    donor_name=donor_name,
                    member_id=member_id,
                    site_id=site_id,
                    campaign_id=campaign_id,
                    success_url=success_url,
                    cancel_url=cancel_url,
                )
            
            return JsonResponse(result)
        
        except (ValueError, InvalidOperation) as e:
            logger.warning(f"Donation validation error: {e}")
            return JsonResponse({
                'error': 'Données de don invalides. Veuillez vérifier le montant et réessayer.'
            }, status=400)
        except Exception as e:
            logger.error(f"Donation session creation error: {e}", exc_info=True)
            return JsonResponse({
                'error': 'Une erreur est survenue lors du traitement. Veuillez réessayer.'
            }, status=500)


class DonationSuccessView(TemplateView):
    """Page de succès après un don."""
    template_name = 'finance/donation_success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['settings'] = SiteSettings.get_settings()
        context['menu_pages'] = PageContent.objects.filter(
            is_published=True,
            show_in_menu=True
        ).order_by('menu_order')
        
        session_id = (self.request.GET.get('session_id') or '').strip()
        if session_id:
            try:
                donation = OnlineDonation.objects.get(stripe_session_id=session_id)
                context['donation'] = donation
            except OnlineDonation.DoesNotExist:
                if session_id == '{CHECKOUT_SESSION_ID}' or not session_id.startswith('cs_'):
                    logger.info("Ignoring invalid success session_id: %s", session_id)
                else:
                    # Fallback: finaliser côté serveur si le webhook Stripe n'est pas encore passé.
                    try:
                        stripe_service.finalize_checkout_session(session_id)
                        donation = OnlineDonation.objects.filter(stripe_session_id=session_id).first()
                        if donation:
                            context['donation'] = donation
                    except Exception:
                        logger.warning(
                            "Unable to finalize checkout session from success page: %s",
                            session_id,
                            exc_info=True,
                        )
        
        return context


class DonationCancelView(TemplateView):
    """Page d'annulation de don."""
    template_name = 'finance/donation_cancel.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['settings'] = SiteSettings.get_settings()
        context['menu_pages'] = PageContent.objects.filter(
            is_published=True,
            show_in_menu=True
        ).order_by('menu_order')
        return context


class DonationReceiptPDFView(View):
    """Télécharge le reçu PDF d'un don en ligne."""
    
    def get(self, request, session_id):
        try:
            donation = OnlineDonation.objects.get(
                stripe_session_id=session_id,
                status='completed',
            )
        except OnlineDonation.DoesNotExist:
            return HttpResponse("Don introuvable.", status=404)
        
        from .pdf_service import generate_donation_receipt_pdf
        
        try:
            pdf_bytes, receipt_number = generate_donation_receipt_pdf(donation)
        except Exception:
            logger.error(f"PDF generation failed for donation {session_id}", exc_info=True)
            return HttpResponse("Erreur lors de la génération du reçu.", status=500)
        
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="recu_don_{receipt_number}.pdf"'
        return response


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
