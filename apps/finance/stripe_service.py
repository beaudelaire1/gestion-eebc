"""
Service de Paiement Stripe pour les dons en ligne EEBC.

Gère :
- Création de sessions de paiement
- Webhooks Stripe
- Enregistrement des transactions
"""

import stripe
import logging
import hashlib
from decimal import Decimal
from django.db.models import F
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)


class StripeService:
    """Service pour gérer les paiements Stripe."""
    
    def __init__(self):
        self.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
        self.public_key = getattr(settings, 'STRIPE_PUBLIC_KEY', None)
        self.webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)

        self.api_key = self._sanitize_key(self.api_key, key_type='secret')
        self.public_key = self._sanitize_key(self.public_key, key_type='public')

        if self.api_key:
            stripe.api_key = self.api_key

    @staticmethod
    def _sanitize_key(raw_key, key_type='secret'):
        """Nettoie/valide une clé Stripe issue de la configuration."""
        if not raw_key:
            return ''

        key = str(raw_key).strip()
        if not key:
            return ''

        # Cas fréquent de mauvaise config sur l'hébergeur: valeur littérale Python.
        if key.startswith('os.environ.get('):
            logger.error(
                "Configuration Stripe invalide: la clé %s contient une expression os.environ.get(...) au lieu d'une vraie clé.",
                key_type,
            )
            return ''

        if key_type == 'secret' and not (key.startswith('sk_test_') or key.startswith('sk_live_')):
            logger.error("Configuration Stripe invalide: STRIPE_SECRET_KEY n'a pas un format Stripe valide.")
            return ''

        if key_type == 'public' and not (key.startswith('pk_test_') or key.startswith('pk_live_')):
            logger.error("Configuration Stripe invalide: STRIPE_PUBLIC_KEY n'a pas un format Stripe valide.")
            return ''

        return key
    
    @property
    def is_configured(self):
        """Vérifie si Stripe est configuré."""
        return bool(self.api_key and self.public_key)
    
    @staticmethod
    def _generate_idempotency_key(*args):
        """Génère une clé d'idempotence basée sur les paramètres."""
        raw = '|'.join(str(a) for a in args)
        return hashlib.sha256(raw.encode()).hexdigest()[:64]
    
    def create_donation_session(self, amount, donation_type, donor_email=None, 
                                 donor_name=None, member_id=None, site_id=None, campaign_id=None,
                                 success_url=None, cancel_url=None):
        """
        Crée une session de paiement Stripe pour un don.
        
        Args:
            amount: Montant en euros (Decimal ou float)
            donation_type: Type de don ('don', 'dime', 'offrande')
            donor_email: Email du donateur
            donor_name: Nom du donateur
            member_id: ID du membre (si connecté)
            site_id: ID du site concerné
            success_url: URL de redirection après succès
            cancel_url: URL de redirection après annulation
        
        Returns:
            dict: Session Stripe avec url de paiement
        """
        if not self.is_configured:
            raise ValueError("Stripe n'est pas configuré")
        
        # Convertir le montant en centimes
        amount_cents = int(Decimal(str(amount)) * 100)
        
        # Métadonnées pour le webhook
        metadata = {
            'donation_type': donation_type,
            'site_id': str(site_id) if site_id else '',
            'member_id': str(member_id) if member_id else '',
            'campaign_id': str(campaign_id) if campaign_id else '',
        }
        
        # Labels pour les types de dons
        type_labels = {
            'don': 'Don',
            'dime': 'Dîme',
            'offrande': 'Offrande',
        }
        
        try:
            idempotency_key = self._generate_idempotency_key(
                'donation', amount_cents, donation_type, donor_email, 
                member_id, site_id, campaign_id, timezone.now().strftime('%Y%m%d%H%M')
            )
            
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'eur',
                        'product_data': {
                            'name': f"{type_labels.get(donation_type, 'Don')} - EEBC",
                            'description': "Église Évangélique Baptiste de Cabassou",
                        },
                        'unit_amount': amount_cents,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url or settings.STRIPE_SUCCESS_URL,
                cancel_url=cancel_url or settings.STRIPE_CANCEL_URL,
                customer_email=donor_email,
                metadata=metadata,
                payment_intent_data={
                    'metadata': metadata,
                },
                idempotency_key=idempotency_key,
            )
            
            return {
                'session_id': session.id,
                'url': session.url,
                'public_key': self.public_key,
            }
        
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating session: {e}")
            raise
    
    def create_recurring_donation(self, amount, donation_type, interval='month',
                                   donor_email=None, member_id=None, site_id=None, campaign_id=None,
                                   success_url=None, cancel_url=None):
        """
        Crée un don récurrent (abonnement).
        
        Args:
            amount: Montant mensuel en euros
            donation_type: Type de don
            interval: 'month' ou 'year'
            ...
        
        Returns:
            dict: Session Stripe pour abonnement
        """
        if not self.is_configured:
            raise ValueError("Stripe n'est pas configuré")
        
        amount_cents = int(Decimal(str(amount)) * 100)
        
        metadata = {
            'donation_type': donation_type,
            'site_id': str(site_id) if site_id else '',
            'member_id': str(member_id) if member_id else '',
            'campaign_id': str(campaign_id) if campaign_id else '',
            'recurring': 'true',
        }
        
        type_labels = {
            'don': 'Don récurrent',
            'dime': 'Dîme mensuelle',
            'offrande': 'Offrande récurrente',
        }
        
        try:
            # Récupérer ou créer le produit (réutiliser un seul produit par type)
            product_name = f"{type_labels.get(donation_type, 'Don récurrent')} - EEBC"
            products = stripe.Product.search(query=f"name:'{product_name}' AND active:'true'")
            
            if products.data:
                product = products.data[0]
            else:
                product = stripe.Product.create(
                    name=product_name,
                    metadata={'donation_type': donation_type, 'church': 'EEBC'},
                )
            
            # Créer le prix récurrent
            price = stripe.Price.create(
                product=product.id,
                unit_amount=amount_cents,
                currency='eur',
                recurring={'interval': interval},
            )
            
            # Créer la session d'abonnement
            idempotency_key = self._generate_idempotency_key(
                'subscription', amount_cents, donation_type, interval,
                donor_email, member_id, site_id, campaign_id, timezone.now().strftime('%Y%m%d%H%M')
            )
            
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price.id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url or settings.STRIPE_SUCCESS_URL,
                cancel_url=cancel_url or settings.STRIPE_CANCEL_URL,
                customer_email=donor_email,
                metadata=metadata,
                idempotency_key=idempotency_key,
            )
            
            return {
                'session_id': session.id,
                'url': session.url,
                'public_key': self.public_key,
            }
        
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating subscription: {e}")
            raise
    
    def handle_webhook(self, payload, sig_header):
        """
        Traite un webhook Stripe.
        
        Args:
            payload: Corps de la requête (bytes)
            sig_header: Header Stripe-Signature
        
        Returns:
            dict: Résultat du traitement
        """
        if not self.webhook_secret:
            raise ValueError("Webhook secret not configured")
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {e}")
            raise
        
        # Traiter les différents types d'événements
        if event['type'] == 'checkout.session.completed':
            return self._handle_checkout_completed(event['data']['object'])
        
        elif event['type'] == 'payment_intent.succeeded':
            return self._handle_payment_succeeded(event['data']['object'])
        
        elif event['type'] == 'invoice.paid':
            return self._handle_invoice_paid(event['data']['object'])
        
        elif event['type'] == 'customer.subscription.deleted':
            return self._handle_subscription_cancelled(event['data']['object'])
        
        return {'status': 'ignored', 'type': event['type']}
    
    def _handle_checkout_completed(self, session):
        """Traite une session de checkout complétée."""
        from .models import FinancialTransaction, OnlineDonation

        # Normaliser en dict standard : Stripe SDK v5+ retourne des StripeObject
        # qui n'héritent plus de dict. On sérialise via JSON pour garantir un
        # dict standard utilisable avec .get() dans tout le code.
        if not isinstance(session, dict):
            import json as _json
            session = _json.loads(str(session))

        metadata = session.get('metadata', {})
        
        # Récupérer le montant
        amount_cents = session.get('amount_total', 0)
        amount = Decimal(amount_cents) / 100
        
        # Mapper le type de don
        donation_type = metadata.get('donation_type', 'don')
        type_mapping = {
            'don': FinancialTransaction.TransactionType.DON,
            'dime': FinancialTransaction.TransactionType.DIME,
            'offrande': FinancialTransaction.TransactionType.OFFRANDE,
        }

        # Protection idempotence: Stripe peut envoyer plusieurs événements.
        existing_donation = OnlineDonation.objects.filter(stripe_session_id=session['id']).select_related('transaction').first()
        if existing_donation:
            if existing_donation.status != OnlineDonation.Status.COMPLETED:
                existing_donation.status = OnlineDonation.Status.COMPLETED
                if not existing_donation.completed_at:
                    existing_donation.completed_at = timezone.now()
                existing_donation.save(update_fields=['status', 'completed_at'])

            if existing_donation.donor_email and not existing_donation.receipt_email_sent_at:
                self._enqueue_donation_receipt_email(existing_donation.id)

            if existing_donation.transaction:
                return {
                    'status': 'success',
                    'transaction_id': existing_donation.transaction.id,
                    'reference': existing_donation.transaction.reference,
                }
        
        # Créer l'enregistrement du don en ligne
        online_donation = OnlineDonation.objects.create(
            stripe_session_id=session['id'],
            stripe_payment_intent=session.get('payment_intent', ''),
            amount=amount,
            donation_type=donation_type,
            donor_email=(session.get('customer_details') or {}).get('email', '') or session.get('customer_email', ''),
            donor_name=(session.get('customer_details') or {}).get('name', ''),
            status='completed',
            completed_at=timezone.now(),
            site_id=metadata.get('site_id') or None,
            member_id=metadata.get('member_id') or None,
        )
        
        # Créer la transaction financière
        transaction = FinancialTransaction.objects.create(
            amount=amount,
            transaction_type=type_mapping.get(donation_type, FinancialTransaction.TransactionType.DON),
            payment_method=FinancialTransaction.PaymentMethod.CARTE,
            status=FinancialTransaction.Status.VALIDE,
            transaction_date=timezone.now().date(),
            description=f"Don en ligne - {(session.get('customer_details') or {}).get('email', '') or session.get('customer_email', 'Anonyme')}",
            site_id=metadata.get('site_id') or None,
            member_id=metadata.get('member_id') or None,
        )
        
        online_donation.transaction = transaction
        online_donation.save()

        # Rattacher automatiquement le don à une campagne si campaign_id présent.
        campaign_id = metadata.get('campaign_id')
        if campaign_id:
            try:
                from apps.campaigns.models import Campaign, Donation as CampaignDonation
                campaign = Campaign.objects.filter(pk=campaign_id, is_active=True).first()
                if campaign:
                    donor_name = (session.get('customer_details') or {}).get('name', '') or (session.get('customer_details') or {}).get('email', '') or 'Donateur en ligne'
                    CampaignDonation.objects.create(
                        campaign=campaign,
                        donor_name=donor_name,
                        amount=amount,
                        notes='Don en ligne (Stripe) lié à la campagne',
                    )
            except Exception as e:
                logger.warning(f"Campaign donation link failed for campaign_id={campaign_id}: {e}")
        
        # Envoyer un reçu par email (file de retry + fallback immédiat).
        if online_donation.donor_email:
            self._enqueue_donation_receipt_email(online_donation.id)
        
        logger.info(f"Donation processed: {transaction.reference} - {amount}€")
        
        return {
            'status': 'success',
            'transaction_id': transaction.id,
            'reference': transaction.reference,
        }

    def finalize_checkout_session(self, session_id):
        """Finalise une session Stripe côté serveur (fallback si webhook retardé/absent)."""
        if not self.is_configured:
            raise ValueError("Stripe n'est pas configuré")

        normalized_session_id = (session_id or '').strip()
        if (
            not normalized_session_id
            or normalized_session_id == '{CHECKOUT_SESSION_ID}'
            or '{' in normalized_session_id
            or '}' in normalized_session_id
            or not normalized_session_id.startswith('cs_')
        ):
            logger.warning("Invalid checkout session id provided for finalize: %s", session_id)
            return {'status': 'invalid_session_id', 'session_id': session_id}

        try:
            stripe_session = stripe.checkout.Session.retrieve(normalized_session_id)
        except stripe.error.InvalidRequestError as exc:
            logger.warning("Stripe checkout session not found or invalid: %s", normalized_session_id)
            return {
                'status': 'session_not_found',
                'session_id': normalized_session_id,
                'error': str(exc),
            }

        # Normaliser en dict standard : Stripe SDK v5+ retourne des StripeObject
        # qui n'héritent plus de dict. La normalisation se fait ici pour que
        # _handle_checkout_completed et les tests (mocks dict) fonctionnent pareil.
        import json as _json
        session = _json.loads(str(stripe_session)) if not isinstance(stripe_session, dict) else stripe_session

        if session.get('payment_status') != 'paid':
            return {'status': 'pending', 'session_id': normalized_session_id}

        return self._handle_checkout_completed(session)
    
    def _handle_payment_succeeded(self, payment_intent):
        """Traite un paiement réussi."""
        # Généralement déjà traité par checkout.session.completed
        return {'status': 'acknowledged'}
    
    def _handle_invoice_paid(self, invoice):
        """Traite une facture payée (abonnement)."""
        from .models import FinancialTransaction, OnlineDonation
        
        subscription_id = invoice.get('subscription')
        amount_cents = invoice.get('amount_paid', 0)
        amount = Decimal(amount_cents) / 100
        
        # Récupérer les métadonnées de l'abonnement
        metadata = {}
        if subscription_id:
            try:
                subscription = stripe.Subscription.retrieve(subscription_id)
                metadata = subscription.get('metadata', {})
            except stripe.error.StripeError as e:
                logger.warning(f"Failed to retrieve subscription {subscription_id}: {e}")
        
        donation_type = metadata.get('donation_type', 'don')
        type_mapping = {
            'don': FinancialTransaction.TransactionType.DON,
            'dime': FinancialTransaction.TransactionType.DIME,
            'offrande': FinancialTransaction.TransactionType.OFFRANDE,
        }
        
        # Créer la transaction
        transaction = FinancialTransaction.objects.create(
            amount=amount,
            transaction_type=type_mapping.get(donation_type, FinancialTransaction.TransactionType.DON),
            payment_method=FinancialTransaction.PaymentMethod.CARTE,
            status=FinancialTransaction.Status.VALIDE,
            transaction_date=timezone.now().date(),
            description=f"Don récurrent - {invoice.get('customer_email', 'Anonyme')}",
            site_id=metadata.get('site_id') or None,
            member_id=metadata.get('member_id') or None,
        )

        campaign_id = metadata.get('campaign_id')
        if campaign_id:
            try:
                from apps.campaigns.models import Campaign, Donation as CampaignDonation
                campaign = Campaign.objects.filter(pk=campaign_id, is_active=True).first()
                if campaign:
                    donor_name = invoice.get('customer_email') or 'Donateur récurrent'
                    CampaignDonation.objects.create(
                        campaign=campaign,
                        donor_name=donor_name,
                        amount=amount,
                        notes='Don récurrent en ligne (Stripe) lié à la campagne',
                    )
            except Exception as e:
                logger.warning(f"Recurring campaign donation link failed for campaign_id={campaign_id}: {e}")
        
        logger.info(f"Recurring donation processed: {transaction.reference} - {amount}€")
        
        return {
            'status': 'success',
            'transaction_id': transaction.id,
        }
    
    def _handle_subscription_cancelled(self, subscription):
        """Traite l'annulation d'un abonnement."""
        logger.info(f"Subscription cancelled: {subscription['id']}")
        return {'status': 'acknowledged'}

    def _enqueue_donation_receipt_email(self, online_donation_id):
        """Planifie l'envoi du reçu et bascule en fallback synchrone si le broker est indisponible."""
        from .models import OnlineDonation
        from .tasks import send_donation_receipt_email_task

        try:
            send_donation_receipt_email_task.delay(online_donation_id)
        except Exception as exc:
            logger.warning(
                "Failed to enqueue receipt email task for donation #%s, fallback to immediate send: %s",
                online_donation_id,
                exc,
            )
            donation = OnlineDonation.objects.filter(pk=online_donation_id).first()
            if donation:
                self._send_donation_receipt(donation)
    
    def _send_donation_receipt(self, online_donation):
        """Envoie un reçu de don professionnel (PDF + HTML) par email.

        Returns:
            bool: True si l'email est envoyé, sinon False.
        """
        from django.core.mail import EmailMessage
        from django.template.loader import render_to_string
        from apps.communication.models import EmailLog
        from .pdf_service import generate_donation_receipt_pdf

        if not online_donation.donor_email:
            logger.warning("Donation #%s has no donor email, receipt cannot be sent.", online_donation.id)
            return False

        if online_donation.receipt_email_sent_at:
            return True

        OnlineDonationModel = type(online_donation)
        OnlineDonationModel.objects.filter(pk=online_donation.pk).update(
            receipt_email_attempts=F('receipt_email_attempts') + 1
        )
        online_donation.refresh_from_db(fields=['receipt_email_attempts', 'receipt_email_sent_at'])

        if online_donation.receipt_email_sent_at:
            return True
        
        try:
            # Générer le PDF professionnel
            pdf_bytes, receipt_number = generate_donation_receipt_pdf(online_donation)
            
            donor_name = online_donation.donor_name or 'Frère/Sœur'
            ref = online_donation.transaction.reference if online_donation.transaction else receipt_number
            
            # Labels des types de don
            type_labels = {
                'don': 'Don', 'dime': 'Dîme', 'offrande': 'Offrande',
            }
            donation_type_label = type_labels.get(online_donation.donation_type, 'Don')
            
            # Date formatée
            donation_date = online_donation.completed_at.strftime('%d/%m/%Y') if online_donation.completed_at else timezone.now().strftime('%d/%m/%Y')
            
            subject = f"Reçu de don {ref} - EEBC"
            
            # Corps texte (fallback)
            body = f"""Bonjour {donor_name},

Nous vous remercions chaleureusement pour votre {donation_type_label.lower()} de {online_donation.amount}€.

Votre générosité contribue à l'avancement de l'œuvre de Dieu au sein de notre communauté.

Votre reçu de don (PDF) portant la référence {ref} est joint à cet email.

« Chacun donne comme il l'a résolu en son cœur, sans tristesse ni contrainte ; car Dieu aime celui qui donne avec joie. » — 2 Corinthiens 9:7

Que Dieu vous bénisse abondamment.

L'Équipe de Finance EEBC
Église Évangélique Baptiste de Cabassou
11 lot Calimbé 2, rte de Cabassou
97300 Cayenne, Guyane française
"""
            
            # Corps HTML avec template
            html_body = render_to_string('emails/donation_receipt.html', {
                'donor_name': donor_name,
                'amount': online_donation.amount,
                'donation_type_label': donation_type_label,
                'reference': ref,
                'donation_date': donation_date,
            })

            email_log = EmailLog.objects.create(
                recipient_email=online_donation.donor_email,
                recipient_name=donor_name,
                subject=subject,
                body=body,
                status=EmailLog.Status.PENDING,
            )

            from django.core.mail import EmailMultiAlternatives
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=body,
                from_email=None,
                to=[online_donation.donor_email],
            )
            
            # Ajouter le contenu HTML
            email.attach_alternative(html_body, 'text/html')
            
            # Attacher le PDF
            email.attach(
                f"recu_don_{receipt_number}.pdf",
                pdf_bytes,
                'application/pdf'
            )
            
            email.send(fail_silently=False)

            email_log.status = EmailLog.Status.SENT
            email_log.sent_at = timezone.now()
            email_log.error_message = ''
            email_log.save(update_fields=['status', 'sent_at', 'error_message'])

            online_donation.receipt_email_sent_at = timezone.now()
            online_donation.receipt_email_last_error = ''
            online_donation.save(update_fields=['receipt_email_sent_at', 'receipt_email_last_error'])

            logger.info(f"Donation receipt email sent to {online_donation.donor_email}: {receipt_number}")
            return True
            
        except Exception as e:
            error_message = str(e)
            online_donation.receipt_email_last_error = error_message
            online_donation.save(update_fields=['receipt_email_last_error'])
            logger.error(f"Failed to send donation receipt: {e}", exc_info=True)
            return False


# Instance singleton
stripe_service = StripeService()
