"""Vues pour les dons en ligne via Stripe."""

import json
import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core import signing
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from apps.core.models import SiteSettings, PageContent
from apps.core.utils.turnstile import validate_turnstile, get_client_ip

from .stripe_service import stripe_service
from .models import OnlineDonation

logger = logging.getLogger(__name__)

RECEIPT_ACCESS_SALT = 'donation-receipt-access-v1'
RECEIPT_ACCESS_MAX_AGE = 2 * 60 * 60
CHECKOUT_SESSION_KEY = 'donation_checkout_session_id'


class DonationPageView(TemplateView):
    template_name = 'finance/donation_page.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stripe_public_key'] = stripe_service.public_key
        context['stripe_configured'] = stripe_service.is_configured
        context['settings'] = SiteSettings.get_settings()
        context['menu_pages'] = PageContent.objects.filter(
            is_published=True, show_in_menu=True
        ).order_by('menu_order')
        context['turnstile_site_key'] = getattr(settings, 'TURNSTILE_SITE_KEY', '')

        from apps.core.models import Site
        context['sites'] = Site.objects.filter(is_active=True)

        if self.request.user.is_authenticated:
            context['user_authenticated'] = True
            context['user_email'] = self.request.user.email or ''
            context['user_full_name'] = f"{self.request.user.first_name} {self.request.user.last_name}".strip()
            if hasattr(self.request.user, 'member_profile'):
                member = self.request.user.member_profile
                context['user_full_name'] = member.full_name or context['user_full_name']
                context['user_member_id'] = member.id
        else:
            context['user_authenticated'] = False

        token = self.request.GET.get('c')
        selected_campaign = None
        if isinstance(token, str) and token:
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
    def post(self, request):
        if not stripe_service.is_configured:
            return JsonResponse({'error': "Le paiement en ligne n'est pas configuré"}, status=400)

        try:
            data = json.loads(request.body)
            turnstile_token = data.get('turnstile_token')
            ip_address = get_client_ip(request)
            is_valid, captcha_error = validate_turnstile(turnstile_token, ip_address)
            if not is_valid:
                return JsonResponse({'error': captcha_error or 'Vérification de sécurité échouée.'}, status=403)

            amount = Decimal(data.get('amount', 0))
            if amount < 1:
                return JsonResponse({'error': 'Le montant minimum est de 1€'}, status=400)

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

            member_id = None
            if request.user.is_authenticated and hasattr(request.user, 'member_profile'):
                member_id = request.user.member_profile.id

            success_url = request.build_absolute_uri('/don/succes/') + '?session_id={CHECKOUT_SESSION_ID}'
            cancel_url = request.build_absolute_uri('/don/annule/')
            if not settings.DEBUG:
                success_url = success_url.replace('http://', 'https://')
                cancel_url = cancel_url.replace('http://', 'https://')

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

            # Bind the future Stripe redirect to the browser that initiated checkout.
            session_id = result.get('session_id') if isinstance(result, dict) else None
            if session_id:
                request.session[CHECKOUT_SESSION_KEY] = session_id
                request.session.modified = True

            return JsonResponse(result)

        except (ValueError, InvalidOperation) as exc:
            logger.warning('Donation validation error: %s', exc)
            return JsonResponse({'error': 'Données de don invalides. Veuillez vérifier le montant et réessayer.'}, status=400)
        except Exception as exc:
            logger.error('Donation session creation error: %s', exc, exc_info=True)
            return JsonResponse({'error': 'Une erreur est survenue lors du traitement. Veuillez réessayer.'}, status=500)


class DonationSuccessView(TemplateView):
    template_name = 'finance/donation_success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['settings'] = SiteSettings.get_settings()
        context['menu_pages'] = PageContent.objects.filter(
            is_published=True, show_in_menu=True
        ).order_by('menu_order')
        context['payment_confirmed'] = False

        session_id = (self.request.GET.get('session_id') or '').strip()
        bound_to_browser = bool(
            session_id and self.request.session.get(CHECKOUT_SESSION_KEY) == session_id
        )
        if not bound_to_browser:
            # A leaked Stripe session id is not a capability to read donor data.
            return context

        donation = OnlineDonation.objects.filter(stripe_session_id=session_id).first()
        if not donation and session_id.startswith('cs_'):
            try:
                stripe_service.finalize_checkout_session(session_id)
                donation = OnlineDonation.objects.filter(stripe_session_id=session_id).first()
            except Exception:
                logger.warning('Unable to finalize checkout session from success page: %s', session_id, exc_info=True)

        if donation:
            context['donation'] = donation
            context['payment_confirmed'] = donation.status == 'completed'
            session_key = self.request.session.session_key
            if session_key:
                context['receipt_access_token'] = signing.dumps(
                    {'session_id': session_id, 'browser_session': session_key},
                    salt=RECEIPT_ACCESS_SALT,
                    compress=True,
                )
        return context


class DonationCancelView(TemplateView):
    template_name = 'finance/donation_cancel.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['settings'] = SiteSettings.get_settings()
        context['menu_pages'] = PageContent.objects.filter(
            is_published=True, show_in_menu=True
        ).order_by('menu_order')
        return context


class DonationReceiptPDFView(View):
    def _authorized(self, request, donation, session_id):
        if request.user.is_authenticated:
            member_user_id = getattr(getattr(donation, 'member', None), 'user_id', None)
            if member_user_id == request.user.id or (
                donation.donor_email and request.user.email and
                donation.donor_email.lower() == request.user.email.lower()
            ):
                return True

        token = request.GET.get('token') or ''
        if not token or not request.session.session_key:
            return False
        try:
            payload = signing.loads(token, salt=RECEIPT_ACCESS_SALT, max_age=RECEIPT_ACCESS_MAX_AGE)
        except (signing.BadSignature, signing.SignatureExpired):
            return False
        return (
            payload.get('session_id') == session_id
            and payload.get('browser_session') == request.session.session_key
            and request.session.get(CHECKOUT_SESSION_KEY) == session_id
        )

    def get(self, request, session_id):
        donation = OnlineDonation.objects.filter(
            stripe_session_id=session_id,
            status='completed',
        ).select_related('member').first()
        if not donation:
            return HttpResponse('Don introuvable.', status=404)
        if not self._authorized(request, donation, session_id):
            # Do not reveal whether a captured Stripe id is valid.
            return HttpResponse('Don introuvable.', status=404)

        from .pdf_service import generate_donation_receipt_pdf
        try:
            pdf_bytes, receipt_number = generate_donation_receipt_pdf(donation)
        except Exception:
            logger.error('PDF generation failed for donation %s', session_id, exc_info=True)
            return HttpResponse('Erreur lors de la génération du reçu.', status=500)

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="recu_don_{receipt_number}.pdf"'
        response['Cache-Control'] = 'private, no-store'
        return response


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        logger.info('Stripe webhook received, sig_header present: %s', bool(sig_header))
        try:
            result = stripe_service.handle_webhook(payload, sig_header)
            logger.info('Stripe webhook processed: %s', result.get('status', 'unknown'))
            return JsonResponse(result)
        except ValueError as exc:
            logger.error('Stripe webhook ValueError: %s', exc)
            return HttpResponse(status=400)
        except Exception as exc:
            logger.error('Stripe webhook error: %s', exc, exc_info=True)
            return HttpResponse(status=400)
