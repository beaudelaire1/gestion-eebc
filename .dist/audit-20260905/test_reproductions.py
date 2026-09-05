"""Audit-only reproductions: passing means the observed vulnerability exists.

SQLite test database and synthetic accounts only. Never run against production.
"""
import pytest
from rest_framework.test import APIClient
from django.test import Client
from apps.communication.models import Announcement
from apps.finance.models import OnlineDonation, FinancialTransaction
from test_factories import UserFactory, FinancialTransactionFactory

pytestmark = pytest.mark.django_db

def test_anonymous_reads_staff_announcement():
    a=Announcement.objects.create(title='AUDIT STAFF ONLY',content='Synthetic private content',visibility='staff')
    r=APIClient().get(f'/api/v1/announcements/{a.pk}/')
    assert r.status_code==200
    assert r.json()['content']=='Synthetic private content'

def test_member_can_patch_and_delete_own_donation():
    u=UserFactory(email='audit-own@example.test')
    d=OnlineDonation.objects.create(stripe_session_id='audit-synthetic',amount='50.00',donor_email=u.email,status='completed')
    c=APIClient();c.force_authenticate(u)
    r=c.patch(f'/api/v1/donations/{d.pk}/',{'amount':'1.00','status':'refunded'},format='json')
    assert r.status_code==200
    d.refresh_from_db();assert str(d.amount)=='1.00' and d.status=='refunded'
    r=c.delete(f'/api/v1/donations/{d.pk}/');assert r.status_code==204
    assert not OnlineDonation.objects.filter(pk=d.pk).exists()

def test_changing_email_grants_other_donor_history():
    victim=UserFactory(email='audit-victim@example.test')
    u=UserFactory(email='audit-attacker@example.test')
    d=OnlineDonation.objects.create(stripe_session_id='audit-victim-donation',amount='99.00',donor_email=victim.email,status='completed')
    c=APIClient();c.force_authenticate(u)
    assert c.get(f'/api/v1/donations/{d.pk}/').status_code==404
    assert c.put('/api/v1/profile/',{'email':victim.email},format='json').status_code==200
    u.refresh_from_db();c.force_authenticate(u)
    assert c.get(f'/api/v1/donations/{d.pk}/').status_code==200

def test_driver_global_search_reads_financial_transaction():
    u=UserFactory(role='chauffeur')
    tx=FinancialTransactionFactory(description='AUDIT_PRIVATE_FINANCE',amount='4321.00')
    c=Client();c.force_login(u)
    r=c.get('/app/search/',{'q':'AUDIT_PRIVATE_FINANCE'},HTTP_ACCEPT='application/json')
    assert r.status_code==200
    assert any(x['id']==tx.pk and x['amount']=='4321.00' for x in r.json()['transactions'])

def test_checkout_partial_failure_cannot_recover(monkeypatch):
    from apps.finance.stripe_service import stripe_service
    from django.db import IntegrityError, transaction
    session={'id':'audit-partial-checkout','amount_total':5000,'customer_email':'','metadata':{}}
    original=FinancialTransaction.objects.create
    def fail(**kw):raise RuntimeError('Simulated transaction write failure')
    monkeypatch.setattr(FinancialTransaction.objects,'create',fail)
    with pytest.raises(RuntimeError):stripe_service._handle_checkout_completed(session)
    assert OnlineDonation.objects.filter(stripe_session_id=session['id'],transaction__isnull=True).exists()
    monkeypatch.setattr(FinancialTransaction.objects,'create',original)
    with pytest.raises(IntegrityError),transaction.atomic():stripe_service._handle_checkout_completed(session)
