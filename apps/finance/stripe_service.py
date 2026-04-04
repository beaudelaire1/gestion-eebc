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
        
        if self.api_key:
            stripe.api_key = self.api_key
    
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
        
        # Créer l'enregistrement du don en ligne
        online_donation = OnlineDonation.objects.create(
            stripe_session_id=session['id'],
            stripe_payment_intent=session.get('payment_intent', ''),
            amount=amount,
            donation_type=donation_type,
            donor_email=session.get('customer_email', ''),
            status='completed',
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
            description=f"Don en ligne - {session.get('customer_email', 'Anonyme')}",
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
                    donor_name = session.get('customer_details', {}).get('name') or session.get('customer_email', 'Donateur en ligne')
                    CampaignDonation.objects.create(
                        campaign=campaign,
                        donor_name=donor_name,
                        amount=amount,
                        notes='Don en ligne (Stripe) lié à la campagne',
                    )
            except Exception as e:
                logger.warning(f"Campaign donation link failed for campaign_id={campaign_id}: {e}")
        
        # Envoyer un reçu par email
        if session.get('customer_email'):
            self._send_donation_receipt(online_donation)
        
        logger.info(f"Donation processed: {transaction.reference} - {amount}€")
        
        return {
            'status': 'success',
            'transaction_id': transaction.id,
            'reference': transaction.reference,
        }
    
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
    
    def _send_donation_receipt(self, online_donation):
        """Envoie un reçu de don professionnel (PDF) par email."""
        from django.core.mail import EmailMessage
        from .pdf_service import generate_donation_receipt_pdf
        
        try:
            # Générer le PDF professionnel
            pdf_bytes, receipt_number = generate_donation_receipt_pdf(online_donation)
            
            donor_name = online_donation.donor_name or 'Frère/Sœur'
            ref = online_donation.transaction.reference if online_donation.transaction else receipt_number
            
            # Corps de l'email (texte)
            body = f"""Bonjour {donor_name},

Nous vous remercions chaleureusement pour votre don de {online_donation.amount}€ \
({online_donation.get_donation_type_display()}).

Votre générosité contribue à l'avancement de l'œuvre de Dieu au sein de notre communauté.

Vous trouverez ci-joint votre reçu de don (PDF) portant la référence {ref}.

« Chacun donne comme il l'a résolu en son cœur, sans tristesse ni contrainte ; \
car Dieu aime celui qui donne avec joie. » — 2 Corinthiens 9:7

Que Dieu vous bénisse abondamment,
Église Évangélique Baptiste de Cabassou
"""
            
            email = EmailMessage(
                subject=f"Reçu de don {ref} - EEBC",
                body=body,
                from_email=None,  # Utilise DEFAULT_FROM_EMAIL
                to=[online_donation.donor_email],
            )
            
            # Attacher le PDF
            email.attach(
                f"recu_don_{receipt_number}.pdf",
                pdf_bytes,
                'application/pdf'
            )
            
            email.send()
            logger.info(f"Donation receipt email sent to {online_donation.donor_email}: {receipt_number}")
            
        except Exception as e:
            logger.error(f"Failed to send donation receipt: {e}", exc_info=True)


# Instance singleton
stripe_service = StripeService()
