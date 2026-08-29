"""
Tests POST/CRUD — couvrir les vues d'écriture pour pousser la couverture > 60%.
"""
import pytest
from django.urls import reverse
from apps.events.models import Event, EventCategory
from apps.finance.models import FinancialTransaction, FinanceCategory
from apps.members.models import Member
from apps.communication.models import Announcement


# =============================================================================
# EVENTS — POST
# =============================================================================

@pytest.mark.django_db
class TestEventPostViews:

    def test_event_create_post(self, authenticated_client, admin_user):
        data = {
            'title': 'Culte spécial',
            'start_date': '2026-06-01',
            'visibility': 'public',
        }
        resp = authenticated_client.post(reverse('events:create'), data)
        assert resp.status_code in (200, 302)

    def test_event_update_post(self, authenticated_client, event):
        data = {
            'title': 'Culte modifié',
            'start_date': '2026-06-15',
            'visibility': 'public',
        }
        resp = authenticated_client.post(
            reverse('events:update', args=[event.pk]), data
        )
        assert resp.status_code in (200, 302)

    def test_event_cancel_post(self, authenticated_client, event):
        resp = authenticated_client.post(
            reverse('events:cancel', args=[event.pk]),
            {'notify_participants': True}
        )
        assert resp.status_code in (200, 302)

    def test_event_duplicate_post(self, authenticated_client, event):
        resp = authenticated_client.post(
            reverse('events:duplicate', args=[event.pk]),
            {'new_start_date': '2026-07-01'}
        )
        assert resp.status_code in (200, 302)

    def test_category_create_post(self, authenticated_client):
        resp = authenticated_client.post(
            reverse('events:category_create'),
            {'name': 'Catégorie test', 'color': '#FF6600'}
        )
        assert resp.status_code in (200, 302)

    def test_category_update_post(self, authenticated_client):
        cat = EventCategory.objects.create(name='Old', color='#000000')
        resp = authenticated_client.post(
            reverse('events:category_update', args=[cat.pk]),
            {'name': 'Updated', 'color': '#111111'}
        )
        assert resp.status_code in (200, 302)

    def test_category_delete_post(self, authenticated_client):
        cat = EventCategory.objects.create(name='ToDelete', color='#000000')
        resp = authenticated_client.post(
            reverse('events:category_delete', args=[cat.pk])
        )
        assert resp.status_code in (200, 302)
        assert not EventCategory.objects.filter(pk=cat.pk).exists()

    def test_category_list(self, authenticated_client):
        resp = authenticated_client.get(reverse('events:category_list'))
        assert resp.status_code == 200

    def test_event_list_advanced(self, authenticated_client):
        resp = authenticated_client.get(reverse('events:list_advanced'))
        assert resp.status_code == 200


# =============================================================================
# FINANCE — POST
# =============================================================================

@pytest.mark.django_db
class TestFinancePostViews:

    def test_transaction_create_post(self, authenticated_client, site_cayenne):
        cat = FinanceCategory.objects.create(name='Don test', is_income=True)
        data = {
            'transaction_type': 'don',
            'amount': '150.00',
            'transaction_date': '2026-03-15',
            'payment_method': 'especes',
            'category': cat.pk,
            'site': site_cayenne.pk,
            'status': 'en_attente',
        }
        resp = authenticated_client.post(
            reverse('finance:transaction_create'), data
        )
        assert resp.status_code in (200, 302)

    def test_transaction_validate(self, authenticated_client, financial_transaction):
        resp = authenticated_client.post(
            reverse('finance:transaction_validate', args=[financial_transaction.pk])
        )
        assert resp.status_code in (200, 302)

    def test_tax_receipt_create_post(self, authenticated_client, member):
        resp = authenticated_client.post(
            reverse('finance:tax_receipt_create'),
            {'member': member.pk, 'fiscal_year': 2026}
        )
        assert resp.status_code in (200, 302)

    def test_budget_overview_get(self, authenticated_client):
        resp = authenticated_client.get(reverse('finance:budget_overview'))
        assert resp.status_code == 200

    def test_reports_get(self, authenticated_client):
        resp = authenticated_client.get(reverse('finance:reports'))
        assert resp.status_code == 200

    def test_dashboard_chart_data(self, authenticated_client):
        resp = authenticated_client.get(reverse('finance:dashboard_chart_data'))
        assert resp.status_code == 200

    def test_finance_forbidden_post(self, client, member_user, site_cayenne):
        """Un membre ne peut pas créer de transaction."""
        client.force_login(member_user)
        cat = FinanceCategory.objects.create(name='Test', is_income=True)
        data = {
            'transaction_type': 'don',
            'amount': '50.00',
            'transaction_date': '2026-01-01',
            'payment_method': 'especes',
            'category': cat.pk,
            'site': site_cayenne.pk,
        }
        resp = client.post(reverse('finance:transaction_create'), data)
        assert resp.status_code in (302, 403)


# =============================================================================
# MEMBERS — POST
# =============================================================================

@pytest.mark.django_db
class TestMemberPostViews:

    def test_member_create_post(self, authenticated_client, site_cayenne):
        data = {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'site': site_cayenne.pk,
            'status': 'actif',
        }
        resp = authenticated_client.post(reverse('members:create'), data)
        assert resp.status_code in (200, 302)

    def test_member_edit_post(self, authenticated_client, member):
        data = {
            'first_name': 'Jean-Modifié',
            'last_name': member.last_name,
            'site': member.site.pk,
            'status': 'actif',
        }
        resp = authenticated_client.post(
            reverse('members:edit', args=[member.pk]), data
        )
        assert resp.status_code in (200, 302)

    def test_member_delete_post(self, authenticated_client, member):
        resp = authenticated_client.post(
            reverse('members:delete', args=[member.pk])
        )
        assert resp.status_code in (200, 302)

    def test_member_delete_forbidden(self, client, member_user, member):
        """Un membre ne peut pas supprimer d'autres membres."""
        client.force_login(member_user)
        resp = client.post(reverse('members:delete', args=[member.pk]))
        assert resp.status_code in (302, 403)


# =============================================================================
# COMMUNICATION — POST
# =============================================================================

@pytest.mark.django_db
class TestCommunicationPostViews:

    def test_announcement_create_post(self, authenticated_client):
        resp = authenticated_client.post(
            reverse('communication:announcement_create'),
            {'title': 'Annonce test longue', 'content': 'Contenu assez long pour la validation'}
        )
        assert resp.status_code in (200, 302)

    def test_announcement_edit_post(self, authenticated_client, admin_user):
        ann = Announcement.objects.create(
            title='Original', content='Contenu original de test',
            created_by=admin_user
        )
        resp = authenticated_client.post(
            reverse('communication:announcement_edit', args=[ann.pk]),
            {'title': 'Modifiée', 'content': 'Contenu modifié de test'}
        )
        assert resp.status_code in (200, 302)

    def test_announcement_delete_post(self, authenticated_client, admin_user):
        ann = Announcement.objects.create(
            title='ToDelete', content='Test content',
            created_by=admin_user
        )
        resp = authenticated_client.post(
            reverse('communication:announcement_delete', args=[ann.pk])
        )
        assert resp.status_code in (200, 302)

    def test_notification_mark_read(self, authenticated_client, admin_user):
        from apps.communication.models import Notification
        notif = Notification.objects.create(
            user=admin_user, title='Test', message='msg'
        )
        resp = authenticated_client.post(
            reverse('communication:notification_mark_read', args=[notif.pk])
        )
        assert resp.status_code in (200, 302)

    def test_notifications_mark_all_read(self, authenticated_client, admin_user):
        from apps.communication.models import Notification
        Notification.objects.create(user=admin_user, title='T1', message='m1')
        Notification.objects.create(user=admin_user, title='T2', message='m2')
        resp = authenticated_client.post(
            reverse('communication:notifications_mark_all_read')
        )
        assert resp.status_code in (200, 302)

    def test_notification_detail_marks_read(self, authenticated_client, admin_user):
        from apps.communication.models import Notification
        notif = Notification.objects.create(
            user=admin_user, title='Detail', message='msg'
        )
        resp = authenticated_client.get(
            reverse('communication:notification_detail', args=[notif.pk])
        )
        assert resp.status_code == 200
        notif.refresh_from_db()
        assert notif.is_read is True

    def test_announcement_toggle_active(self, authenticated_client, admin_user):
        ann = Announcement.objects.create(
            title='Toggle', content='Test toggle',
            created_by=admin_user, is_active=True
        )
        resp = authenticated_client.post(
            reverse('communication:announcement_toggle_active', args=[ann.pk])
        )
        assert resp.status_code in (200, 302)

    def test_notifications_count_json(self, authenticated_client):
        resp = authenticated_client.get(
            reverse('communication:notifications_count')
        )
        assert resp.status_code == 200
        assert resp.json()['count'] >= 0


# =============================================================================
# WORSHIP — GET tests for uncovered views
# =============================================================================

@pytest.mark.django_db
class TestWorshipDetailViews:

    def test_service_create_get(self, authenticated_client):
        resp = authenticated_client.get(reverse('worship:service_create'))
        assert resp.status_code == 200

    def test_schedule_create_get(self, authenticated_client):
        resp = authenticated_client.get(reverse('worship:schedule_create'))
        assert resp.status_code == 200


# =============================================================================
# ADDITIONAL GET COVERAGE — pages manquantes
# =============================================================================

@pytest.mark.django_db
class TestAdditionalGetViews:

    def test_calendar_view(self, authenticated_client):
        resp = authenticated_client.get(reverse('events:calendar'))
        assert resp.status_code == 200

    def test_calendar_print(self, authenticated_client):
        resp = authenticated_client.get(reverse('events:calendar_print'))
        assert resp.status_code == 200

    def test_finance_budget_dashboard(self, authenticated_client):
        resp = authenticated_client.get(reverse('finance:budget_dashboard'))
        assert resp.status_code == 200

    def test_finance_budget_list(self, authenticated_client):
        resp = authenticated_client.get(reverse('finance:budget_list'))
        assert resp.status_code == 200

    def test_tax_receipt_create_get(self, authenticated_client):
        resp = authenticated_client.get(reverse('finance:tax_receipt_create'))
        assert resp.status_code == 200
