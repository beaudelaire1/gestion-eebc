import pytest

from apps.finance.models import FinancialTransaction, OnlineDonation
from apps.finance.stripe_service import stripe_service


@pytest.mark.django_db
def test_handle_checkout_completed_is_idempotent(monkeypatch):
    """Un même événement checkout.session.completed ne doit pas créer de doublons."""
    monkeypatch.setattr(stripe_service, '_send_donation_receipt', lambda donation: None)

    session = {
        'id': 'cs_test_idempotent_001',
        'amount_total': 2500,
        'payment_intent': 'pi_test_001',
        'customer_email': 'donateur@example.com',
        'customer_details': {'name': 'Jean Test'},
        'metadata': {
            'donation_type': 'don',
            'site_id': '',
            'member_id': '',
            'campaign_id': '',
        },
    }

    result_1 = stripe_service._handle_checkout_completed(session)
    result_2 = stripe_service._handle_checkout_completed(session)

    assert OnlineDonation.objects.filter(stripe_session_id='cs_test_idempotent_001').count() == 1
    assert FinancialTransaction.objects.filter(online_donation__stripe_session_id='cs_test_idempotent_001').count() == 1
    assert result_1['status'] == 'success'
    assert result_2['status'] == 'success'


@pytest.mark.django_db
def test_finalize_checkout_session_returns_pending_for_unpaid(monkeypatch):
    """Le fallback ne finalise pas une session non payée."""

    class FakeCheckoutSession:
        @staticmethod
        def retrieve(session_id):
            return {
                'id': session_id,
                'payment_status': 'unpaid',
            }

    class FakeCheckout:
        Session = FakeCheckoutSession

    class FakeStripe:
        checkout = FakeCheckout

    monkeypatch.setattr('apps.finance.stripe_service.stripe', FakeStripe)
    monkeypatch.setattr(stripe_service, 'api_key', 'sk_test_dummy')
    monkeypatch.setattr(stripe_service, 'public_key', 'pk_test_dummy')

    result = stripe_service.finalize_checkout_session('cs_test_unpaid_001')

    assert result == {'status': 'pending', 'session_id': 'cs_test_unpaid_001'}


@pytest.mark.django_db
def test_finalize_checkout_session_processes_paid_session(monkeypatch):
    """Le fallback déclenche le traitement normal quand Stripe confirme 'paid'."""

    session_payload = {
        'id': 'cs_test_paid_001',
        'payment_status': 'paid',
    }

    class FakeCheckoutSession:
        @staticmethod
        def retrieve(session_id):
            assert session_id == 'cs_test_paid_001'
            return session_payload

    class FakeCheckout:
        Session = FakeCheckoutSession

    class FakeStripe:
        checkout = FakeCheckout

    captured = {}

    def fake_handle_checkout_completed(session):
        captured['session'] = session
        return {'status': 'success', 'transaction_id': 123, 'reference': 'TRX-TEST-123'}

    monkeypatch.setattr('apps.finance.stripe_service.stripe', FakeStripe)
    monkeypatch.setattr(stripe_service, 'api_key', 'sk_test_dummy')
    monkeypatch.setattr(stripe_service, 'public_key', 'pk_test_dummy')
    monkeypatch.setattr(stripe_service, '_handle_checkout_completed', fake_handle_checkout_completed)

    result = stripe_service.finalize_checkout_session('cs_test_paid_001')

    assert captured['session'] == session_payload
    assert result['status'] == 'success'
    assert result['transaction_id'] == 123


@pytest.mark.django_db
def test_send_donation_receipt_updates_delivery_tracking(monkeypatch):
    """L'envoi de reçu met à jour les champs de suivi dans OnlineDonation."""
    donation = OnlineDonation.objects.create(
        stripe_session_id='cs_test_tracking_001',
        amount='10.00',
        donation_type='don',
        donor_email='donateur@example.com',
        donor_name='Donateur Test',
        status='completed',
    )

    class FakeEmailMessage:
        def __init__(self, *args, **kwargs):
            self.attachments = []

        def attach(self, filename, content, mimetype):
            self.attachments.append((filename, mimetype))

        def send(self, fail_silently=False):
            return 1

    monkeypatch.setattr('apps.finance.stripe_service.EmailMessage', FakeEmailMessage, raising=False)
    monkeypatch.setattr(
        'apps.finance.pdf_service.generate_donation_receipt_pdf',
        lambda d: (b'PDF', 'DON-TEST-00001')
    )

    sent = stripe_service._send_donation_receipt(donation)
    donation.refresh_from_db()

    assert sent is True
    assert donation.receipt_email_attempts == 1
    assert donation.receipt_email_sent_at is not None
    assert donation.receipt_email_last_error == ''


@pytest.mark.django_db
def test_enqueue_receipt_email_fallbacks_to_sync_when_queue_is_unavailable(monkeypatch):
    """Si Celery/Broker tombe, le service bascule en envoi immédiat."""
    donation = OnlineDonation.objects.create(
        stripe_session_id='cs_test_fallback_001',
        amount='15.00',
        donation_type='don',
        donor_email='donateur@example.com',
        status='completed',
    )

    class FakeTask:
        @staticmethod
        def delay(_donation_id):
            raise RuntimeError('broker down')

    called = {'sync': False}

    def fake_send_sync(d):
        called['sync'] = True
        return True

    monkeypatch.setattr('apps.finance.tasks.send_donation_receipt_email_task', FakeTask)
    monkeypatch.setattr(stripe_service, '_send_donation_receipt', fake_send_sync)

    stripe_service._enqueue_donation_receipt_email(donation.id)

    assert called['sync'] is True


@pytest.mark.django_db
def test_finalize_checkout_session_rejects_placeholder_value(monkeypatch):
    """Le placeholder Stripe ne doit jamais déclencher un appel API Stripe."""

    class FakeCheckoutSession:
        @staticmethod
        def retrieve(session_id):
            raise AssertionError('Stripe retrieve should not be called for placeholder values')

    class FakeCheckout:
        Session = FakeCheckoutSession

    class FakeStripe:
        checkout = FakeCheckout

    monkeypatch.setattr('apps.finance.stripe_service.stripe', FakeStripe)
    monkeypatch.setattr(stripe_service, 'api_key', 'sk_test_dummy')
    monkeypatch.setattr(stripe_service, 'public_key', 'pk_test_dummy')

    result = stripe_service.finalize_checkout_session('{CHECKOUT_SESSION_ID}')

    assert result['status'] == 'invalid_session_id'


@pytest.mark.django_db
def test_finalize_checkout_session_handles_not_found(monkeypatch):
    """Un id de session Stripe inconnu ne doit pas lever d'exception non gérée."""

    class FakeInvalidRequestError(Exception):
        pass

    class FakeCheckoutSession:
        @staticmethod
        def retrieve(session_id):
            raise FakeInvalidRequestError('No such checkout.session')

    class FakeCheckout:
        Session = FakeCheckoutSession

    class FakeStripe:
        checkout = FakeCheckout

        class error:
            InvalidRequestError = FakeInvalidRequestError

    monkeypatch.setattr('apps.finance.stripe_service.stripe', FakeStripe)
    monkeypatch.setattr(stripe_service, 'api_key', 'sk_test_dummy')
    monkeypatch.setattr(stripe_service, 'public_key', 'pk_test_dummy')

    result = stripe_service.finalize_checkout_session('cs_test_unknown_001')

    assert result['status'] == 'session_not_found'
