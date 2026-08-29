"""
Tests de vues — dashboard, members, events, finance, worship.
Objectif : couvrir les vues GET les plus volumineuses pour pousser la couverture > 60%.
"""
import pytest
from django.urls import reverse


# =============================================================================
# DASHBOARD
# =============================================================================

@pytest.mark.django_db
class TestDashboardViews:

    def test_home_authenticated(self, authenticated_client):
        resp = authenticated_client.get(reverse('dashboard:home'))
        assert resp.status_code == 200

    def test_home_anonymous_redirect(self, client):
        resp = client.get(reverse('dashboard:home'))
        assert resp.status_code == 302

    def test_quick_stats(self, authenticated_client):
        resp = authenticated_client.get(reverse('dashboard:stats'))
        assert resp.status_code in (200, 302)


# =============================================================================
# MEMBERS
# =============================================================================

@pytest.mark.django_db
class TestMemberViews:

    def test_member_list(self, authenticated_client, members):
        resp = authenticated_client.get(reverse('members:list'))
        assert resp.status_code == 200

    def test_member_list_empty(self, authenticated_client):
        resp = authenticated_client.get(reverse('members:list'))
        assert resp.status_code == 200

    def test_member_list_search(self, authenticated_client, members):
        resp = authenticated_client.get(reverse('members:list'), {'search': 'Test'})
        assert resp.status_code == 200

    def test_member_detail(self, authenticated_client, member):
        resp = authenticated_client.get(reverse('members:detail', args=[member.pk]))
        assert resp.status_code == 200

    def test_member_create_get(self, authenticated_client):
        resp = authenticated_client.get(reverse('members:create'))
        assert resp.status_code == 200

    def test_member_edit_get(self, authenticated_client, member):
        resp = authenticated_client.get(reverse('members:edit', args=[member.pk]))
        assert resp.status_code == 200

    def test_member_delete_get(self, authenticated_client, member):
        resp = authenticated_client.get(reverse('members:delete', args=[member.pk]))
        assert resp.status_code == 200

    def test_member_list_anonymous_redirect(self, client):
        resp = client.get(reverse('members:list'))
        assert resp.status_code == 302

    def test_member_list_filter_status(self, authenticated_client, members):
        resp = authenticated_client.get(reverse('members:list'), {'status': 'actif'})
        assert resp.status_code == 200

    def test_life_event_list(self, authenticated_client):
        resp = authenticated_client.get(reverse('members:life_events'))
        assert resp.status_code == 200

    def test_visit_list(self, authenticated_client):
        resp = authenticated_client.get(reverse('members:visits'))
        assert resp.status_code == 200

    def test_members_needing_visit(self, authenticated_client):
        resp = authenticated_client.get(reverse('members:members_needing_visit'))
        assert resp.status_code == 200

    def test_member_forbidden_for_basic_member(self, client, member_user):
        """Un utilisateur membre ne peut pas créer de membres."""
        client.force_login(member_user)
        resp = client.get(reverse('members:create'))
        assert resp.status_code in (302, 403)


# =============================================================================
# EVENTS
# =============================================================================

@pytest.mark.django_db
class TestEventViews:

    def test_event_list(self, authenticated_client):
        resp = authenticated_client.get(reverse('events:list'))
        assert resp.status_code == 200

    def test_event_list_show_past(self, authenticated_client, events):
        resp = authenticated_client.get(reverse('events:list'), {'show_past': '1'})
        assert resp.status_code == 200

    def test_event_detail(self, authenticated_client, event):
        resp = authenticated_client.get(reverse('events:detail', args=[event.pk]))
        assert resp.status_code == 200

    def test_calendar_view(self, authenticated_client):
        resp = authenticated_client.get(reverse('events:calendar'))
        assert resp.status_code == 200

    def test_events_json(self, authenticated_client, events):
        resp = authenticated_client.get(reverse('events:events_json'))
        assert resp.status_code == 200
        assert resp['Content-Type'] == 'application/json'

    def test_upcoming_events_partial(self, authenticated_client):
        resp = authenticated_client.get(reverse('events:upcoming'))
        assert resp.status_code == 200

    def test_event_create_get(self, authenticated_client):
        resp = authenticated_client.get(reverse('events:create'))
        assert resp.status_code == 200

    def test_event_list_anonymous_redirect(self, client):
        resp = client.get(reverse('events:list'))
        assert resp.status_code == 302


# =============================================================================
# FINANCE
# =============================================================================

@pytest.mark.django_db
class TestFinanceViews:

    def test_finance_dashboard(self, authenticated_client):
        resp = authenticated_client.get(reverse('finance:dashboard'))
        assert resp.status_code == 200

    def test_transaction_list(self, authenticated_client):
        resp = authenticated_client.get(reverse('finance:transaction_list'))
        assert resp.status_code == 200

    def test_transaction_list_with_data(self, authenticated_client, financial_transactions):
        resp = authenticated_client.get(reverse('finance:transaction_list'))
        assert resp.status_code == 200

    def test_transaction_list_filter(self, authenticated_client):
        resp = authenticated_client.get(
            reverse('finance:transaction_list'),
            {'sort': 'amount', 'order': 'asc'}
        )
        assert resp.status_code == 200

    def test_transaction_detail(self, authenticated_client, financial_transaction):
        resp = authenticated_client.get(
            reverse('finance:transaction_detail', args=[financial_transaction.pk])
        )
        assert resp.status_code == 200

    def test_transaction_create_get(self, authenticated_client):
        resp = authenticated_client.get(reverse('finance:transaction_create'))
        assert resp.status_code == 200

    def test_budget_overview(self, authenticated_client):
        resp = authenticated_client.get(reverse('finance:budget_overview'))
        assert resp.status_code == 200

    def test_reports(self, authenticated_client):
        resp = authenticated_client.get(reverse('finance:reports'))
        assert resp.status_code == 200

    def test_tax_receipt_list(self, authenticated_client):
        resp = authenticated_client.get(reverse('finance:tax_receipt_list'))
        assert resp.status_code == 200

    def test_finance_forbidden_for_member(self, client, member_user):
        client.force_login(member_user)
        resp = client.get(reverse('finance:dashboard'))
        assert resp.status_code in (302, 403)


# =============================================================================
# WORSHIP
# =============================================================================

@pytest.mark.django_db
class TestWorshipViews:

    def test_service_list(self, authenticated_client):
        resp = authenticated_client.get(reverse('worship:service_list'))
        assert resp.status_code == 200

    def test_service_list_all(self, authenticated_client):
        resp = authenticated_client.get(
            reverse('worship:service_list'), {'upcoming': 'false'}
        )
        assert resp.status_code == 200

    def test_monthly_schedule_list(self, authenticated_client):
        resp = authenticated_client.get(reverse('worship:schedule_list'))
        assert resp.status_code == 200


# =============================================================================
# COMMUNICATION
# =============================================================================

@pytest.mark.django_db
class TestCommunicationViews:

    def test_notifications_list(self, authenticated_client):
        resp = authenticated_client.get(reverse('communication:notifications'))
        assert resp.status_code == 200

    def test_announcements(self, authenticated_client):
        resp = authenticated_client.get(reverse('communication:announcements'))
        assert resp.status_code == 200

    def test_email_logs(self, authenticated_client):
        resp = authenticated_client.get(reverse('communication:email_logs'))
        assert resp.status_code == 200

    def test_sms_logs(self, authenticated_client):
        resp = authenticated_client.get(reverse('communication:sms_logs'))
        assert resp.status_code == 200


# =============================================================================
# CAMPAIGNS
# =============================================================================

@pytest.mark.django_db
class TestCampaignViews:

    def test_campaign_list(self, authenticated_client):
        resp = authenticated_client.get(reverse('campaigns:list'))
        assert resp.status_code == 200


# =============================================================================
# GROUPS
# =============================================================================

@pytest.mark.django_db
class TestGroupViews:

    def test_group_list(self, authenticated_client):
        resp = authenticated_client.get(reverse('groups:list'))
        assert resp.status_code == 200


# =============================================================================
# DEPARTMENTS
# =============================================================================

@pytest.mark.django_db
class TestDepartmentViews:

    def test_department_list(self, authenticated_client):
        resp = authenticated_client.get(reverse('departments:list'))
        assert resp.status_code == 200


# =============================================================================
# TRANSPORT
# =============================================================================

@pytest.mark.django_db
class TestTransportViews:

    def test_transport_requests(self, authenticated_client):
        resp = authenticated_client.get(reverse('transport:requests'))
        assert resp.status_code == 200


# =============================================================================
# INVENTORY
# =============================================================================

@pytest.mark.django_db
class TestInventoryViews:

    def test_equipment_list(self, authenticated_client):
        resp = authenticated_client.get(reverse('inventory:list'))
        assert resp.status_code == 200


# =============================================================================
# ACCOUNTS
# =============================================================================

@pytest.mark.django_db
class TestAccountViews:

    def test_login_page(self, client):
        resp = client.get(reverse('accounts:login'))
        assert resp.status_code == 200

    def test_profile_authenticated(self, authenticated_client):
        resp = authenticated_client.get(reverse('accounts:profile'))
        assert resp.status_code == 200

    def test_profile_anonymous_redirect(self, client):
        resp = client.get(reverse('accounts:profile'))
        assert resp.status_code == 302
