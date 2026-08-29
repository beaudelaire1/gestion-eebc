"""
Tests massifs GET/POST pour couvrir toutes les apps — objectif > 60% couverture.
"""
import pytest
from datetime import date, time, timedelta
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


# =============================================================================
# FIXTURES locales
# =============================================================================

@pytest.fixture
def extra_user(db):
    return User.objects.create_user(
        username='extra_test', password='password123',
        first_name='Extra', last_name='User', email='extra@test.com',
    )


# -- GROUP fixtures --
@pytest.fixture
def group(db, site_cayenne):
    from apps.groups.models import Group
    return Group.objects.create(name='Groupe test', site=site_cayenne)


@pytest.fixture
def group_meeting(db, group):
    from apps.groups.models import GroupMeeting
    return GroupMeeting.objects.create(
        group=group, date=date(2026, 6, 1), topic='Étude'
    )


# -- YOUNG fixtures --
@pytest.fixture
def youth_group(db):
    from apps.young.models import YouthGroup
    return YouthGroup.objects.create(name='Ados', min_age=12, max_age=17)


@pytest.fixture
def young_member(db, youth_group, site_cayenne):
    from apps.young.models import YoungMember
    return YoungMember.objects.create(
        first_name='Marie', last_name='Duval',
        date_of_birth=date(2012, 5, 10), gender='F',
        group=youth_group, site=site_cayenne,
    )


@pytest.fixture
def youth_event(db, admin_user, site_cayenne):
    from apps.young.models import YouthEvent
    return YouthEvent.objects.create(
        title='Sortie jeunes', date=date(2026, 7, 15),
        event_type='sortie', site=site_cayenne, created_by=admin_user,
    )


# -- TRANSPORT fixtures --
@pytest.fixture
def driver_profile(db, extra_user):
    from apps.transport.models import DriverProfile
    return DriverProfile.objects.create(
        user=extra_user, vehicle_type='voiture', capacity=5,
    )


@pytest.fixture
def transport_request(db, driver_profile):
    from apps.transport.models import TransportRequest
    return TransportRequest.objects.create(
        requester_name='Paul Martin', requester_phone='0694000000',
        pickup_address='10 rue de la gare', event_date=date(2026, 6, 1),
        event_time=time(9, 0),
    )


# -- BIBLECLUB fixtures --
@pytest.fixture
def bible_class(db, age_group):
    from apps.bibleclub.models import BibleClass
    return BibleClass.objects.create(age_group=age_group, room='Salle A')


@pytest.fixture
def monitor(db, admin_user, bible_class):
    from apps.bibleclub.models import Monitor
    return Monitor.objects.create(user=admin_user, bible_class=bible_class)


@pytest.fixture
def bible_session(db):
    from apps.bibleclub.models import Session
    return Session.objects.create(date=date(2026, 6, 8), theme='Genèse')


# -- INVENTORY fixtures --
@pytest.fixture
def inv_category(db):
    from apps.inventory.models import Category
    return Category.objects.create(name='Mobilier')


@pytest.fixture
def equipment(db, inv_category, admin_user):
    from apps.inventory.models import Equipment
    return Equipment.objects.create(
        name='Chaise', category=inv_category, quantity=50,
        condition='good', responsible=admin_user,
    )


# -- FINANCE budget fixtures --
@pytest.fixture
def budget_category(db):
    from apps.finance.models import BudgetCategory
    return BudgetCategory.objects.create(name='Fonctionnement')


@pytest.fixture
def budget(db, admin_user):
    from apps.finance.models import Budget
    return Budget.objects.create(
        name='Budget 2026', year=2026,
        total_requested=Decimal('10000.00'),
        created_by=admin_user, status='draft',
    )


@pytest.fixture
def budget_request(db, budget_category, admin_user):
    from apps.finance.models import BudgetRequest
    return BudgetRequest.objects.create(
        title='Achat micro', description='Besoin micro HF',
        requested_amount=Decimal('500.00'), category=budget_category,
        requested_by=admin_user, justification='Urgent pour le culte',
    )


# =============================================================================
# GROUPS views
# =============================================================================

@pytest.mark.django_db
class TestGroupViews:

    def test_list(self, authenticated_client, group):
        r = authenticated_client.get(reverse('groups:list'))
        assert r.status_code == 200

    def test_dashboard(self, authenticated_client, group):
        r = authenticated_client.get(reverse('groups:dashboard'))
        assert r.status_code == 200

    def test_create_get(self, authenticated_client):
        r = authenticated_client.get(reverse('groups:create'))
        assert r.status_code == 200

    def test_create_post(self, authenticated_client, site_cayenne):
        r = authenticated_client.post(reverse('groups:create'), {
            'name': 'Nouveau groupe', 'group_type': 'prayer',
            'color': '#FF0000', 'site': site_cayenne.pk,
        })
        assert r.status_code in (200, 302)

    def test_detail(self, authenticated_client, group):
        r = authenticated_client.get(reverse('groups:detail', args=[group.pk]))
        assert r.status_code == 200

    def test_update_get(self, authenticated_client, group):
        r = authenticated_client.get(reverse('groups:update', args=[group.pk]))
        assert r.status_code == 200

    def test_update_post(self, authenticated_client, group):
        r = authenticated_client.post(reverse('groups:update', args=[group.pk]), {
            'name': 'Groupe modifié', 'group_type': 'prayer', 'color': '#00FF00',
        })
        assert r.status_code in (200, 302)

    def test_delete_post(self, authenticated_client, group):
        r = authenticated_client.post(reverse('groups:delete', args=[group.pk]))
        assert r.status_code in (200, 302)

    def test_statistics(self, authenticated_client, group):
        r = authenticated_client.get(reverse('groups:statistics', args=[group.pk]))
        assert r.status_code == 200

    def test_members_manage_get(self, authenticated_client, group):
        r = authenticated_client.get(reverse('groups:members_manage', args=[group.pk]))
        assert r.status_code == 200

    def test_generate_meetings_post(self, authenticated_client, group):
        r = authenticated_client.post(reverse('groups:generate_meetings', args=[group.pk]), {
            'start_date': '2026-06-01', 'end_date': '2026-08-31',
            'frequency': 'weekly', 'day': 'sunday',
        })
        assert r.status_code in (200, 302)

    def test_meeting_create_get(self, authenticated_client, group):
        r = authenticated_client.get(reverse('groups:meeting_create', args=[group.pk]))
        assert r.status_code == 200

    def test_meeting_create_post(self, authenticated_client, group):
        r = authenticated_client.post(reverse('groups:meeting_create', args=[group.pk]), {
            'date': '2026-08-01', 'topic': 'Prière',
        })
        assert r.status_code in (200, 302)

    def test_meeting_update_get(self, authenticated_client, group, group_meeting):
        r = authenticated_client.get(
            reverse('groups:meeting_update', args=[group.pk, group_meeting.pk])
        )
        assert r.status_code == 200

    def test_meeting_delete_post(self, authenticated_client, group, group_meeting):
        r = authenticated_client.post(
            reverse('groups:meeting_delete', args=[group.pk, group_meeting.pk])
        )
        assert r.status_code in (200, 302)


# =============================================================================
# YOUNG views
# =============================================================================

@pytest.mark.django_db
class TestYoungViews:

    def test_home(self, authenticated_client):
        r = authenticated_client.get(reverse('young:home'))
        assert r.status_code == 200

    def test_member_list(self, authenticated_client, young_member):
        r = authenticated_client.get(reverse('young:member_list'))
        assert r.status_code == 200

    def test_member_create_post(self, authenticated_client, youth_group, site_cayenne):
        r = authenticated_client.post(reverse('young:member_create'), {
            'first_name': 'Lucas', 'last_name': 'Bernard',
            'date_of_birth': '2013-03-15', 'gender': 'M',
            'group': youth_group.pk, 'site': site_cayenne.pk, 'status': 'actif',
        })
        assert r.status_code in (200, 302)

    def test_member_detail(self, authenticated_client, young_member):
        r = authenticated_client.get(reverse('young:member_detail', args=[young_member.pk]))
        assert r.status_code == 200

    def test_member_edit_post(self, authenticated_client, young_member, youth_group, site_cayenne):
        r = authenticated_client.post(reverse('young:member_edit', args=[young_member.pk]), {
            'first_name': 'Marie-Édit', 'last_name': 'Duval',
            'date_of_birth': '2012-05-10', 'gender': 'F',
            'group': youth_group.pk, 'site': site_cayenne.pk, 'status': 'actif',
        })
        assert r.status_code in (200, 302)

    def test_member_delete(self, authenticated_client, young_member):
        r = authenticated_client.post(reverse('young:member_delete', args=[young_member.pk]))
        assert r.status_code in (200, 302)

    def test_group_list(self, authenticated_client, youth_group):
        r = authenticated_client.get(reverse('young:group_list'))
        assert r.status_code == 200

    def test_group_create_get(self, authenticated_client):
        r = authenticated_client.get(reverse('young:group_create'))
        assert r.status_code == 200

    def test_group_create_post(self, authenticated_client):
        r = authenticated_client.post(reverse('young:group_create'), {
            'name': 'Petits', 'min_age': 3, 'max_age': 6, 'color': '#FF6600',
        })
        assert r.status_code in (200, 302)

    def test_group_edit_get(self, authenticated_client, youth_group):
        r = authenticated_client.get(reverse('young:group_edit', args=[youth_group.pk]))
        assert r.status_code == 200

    def test_group_delete(self, authenticated_client, youth_group):
        r = authenticated_client.post(reverse('young:group_delete', args=[youth_group.pk]))
        assert r.status_code in (200, 302)

    def test_event_list(self, authenticated_client, youth_event):
        r = authenticated_client.get(reverse('young:event_list'))
        assert r.status_code == 200

    def test_event_create_get(self, authenticated_client):
        r = authenticated_client.get(reverse('young:event_create'))
        assert r.status_code == 200

    def test_event_create_post(self, authenticated_client, site_cayenne):
        r = authenticated_client.post(reverse('young:event_create'), {
            'title': 'Camp été', 'date': '2026-08-01', 'event_type': 'camp',
            'site': site_cayenne.pk,
        })
        assert r.status_code in (200, 302)

    def test_event_detail(self, authenticated_client, youth_event):
        r = authenticated_client.get(reverse('young:event_detail', args=[youth_event.pk]))
        assert r.status_code == 200

    def test_event_edit_get(self, authenticated_client, youth_event):
        r = authenticated_client.get(reverse('young:event_edit', args=[youth_event.pk]))
        assert r.status_code == 200

    def test_take_attendance_get(self, authenticated_client, youth_event):
        r = authenticated_client.get(reverse('young:take_attendance', args=[youth_event.pk]))
        assert r.status_code == 200


# =============================================================================
# TRANSPORT views
# =============================================================================

@pytest.mark.django_db
class TestTransportViews:

    def test_driver_list(self, authenticated_client, driver_profile):
        r = authenticated_client.get(reverse('transport:drivers'))
        assert r.status_code == 200

    def test_driver_create_get(self, authenticated_client):
        r = authenticated_client.get(reverse('transport:driver_create'))
        assert r.status_code == 200

    def test_driver_create_post(self, authenticated_client):
        user = User.objects.create_user(
            username='driver_new', password='password123',
            first_name='Chauffeur', last_name='Nouveau',
        )
        r = authenticated_client.post(reverse('transport:driver_create'), {
            'user': user.pk, 'vehicle_type': 'minibus',
            'capacity': 8, 'is_available': True,
        })
        assert r.status_code in (200, 302)

    def test_driver_detail(self, authenticated_client, driver_profile):
        r = authenticated_client.get(
            reverse('transport:driver_detail', args=[driver_profile.pk])
        )
        assert r.status_code == 200

    def test_driver_update_get(self, authenticated_client, driver_profile):
        r = authenticated_client.get(
            reverse('transport:driver_update', args=[driver_profile.pk])
        )
        assert r.status_code == 200

    def test_driver_delete(self, authenticated_client, driver_profile):
        r = authenticated_client.post(
            reverse('transport:driver_delete', args=[driver_profile.pk])
        )
        assert r.status_code in (200, 302)

    def test_request_list(self, authenticated_client, transport_request):
        r = authenticated_client.get(reverse('transport:requests'))
        assert r.status_code == 200

    def test_request_create_get(self, authenticated_client):
        r = authenticated_client.get(reverse('transport:request_create'))
        assert r.status_code == 200

    def test_request_create_post(self, authenticated_client):
        r = authenticated_client.post(reverse('transport:request_create'), {
            'requester_name': 'Jean Test',
            'requester_phone': '0694111111',
            'pickup_address': '5 avenue des palmiers',
            'event_date': '2026-06-15',
            'event_time': '08:30',
            'passengers_count': 3,
        })
        assert r.status_code in (200, 302)

    def test_request_detail(self, authenticated_client, transport_request):
        r = authenticated_client.get(
            reverse('transport:request_detail', args=[transport_request.pk])
        )
        assert r.status_code == 200

    def test_request_update_get(self, authenticated_client, transport_request):
        r = authenticated_client.get(
            reverse('transport:request_update', args=[transport_request.pk])
        )
        assert r.status_code == 200

    def test_request_delete(self, authenticated_client, transport_request):
        r = authenticated_client.post(
            reverse('transport:request_delete', args=[transport_request.pk])
        )
        assert r.status_code in (200, 302)

    def test_calendar(self, authenticated_client):
        r = authenticated_client.get(reverse('transport:calendar'))
        assert r.status_code == 200

    def test_calendar_data(self, authenticated_client):
        r = authenticated_client.get(reverse('transport:calendar_data'))
        assert r.status_code == 200


# =============================================================================
# BIBLECLUB views
# =============================================================================

@pytest.mark.django_db
class TestBibleClubViews:

    def test_home(self, authenticated_client):
        r = authenticated_client.get(reverse('bibleclub:home'))
        assert r.status_code == 200

    def test_attendance_chart_data(self, authenticated_client):
        r = authenticated_client.get(reverse('bibleclub:attendance_chart_data'))
        assert r.status_code == 200

    def test_class_list(self, authenticated_client, bible_class):
        r = authenticated_client.get(reverse('bibleclub:class_list'))
        assert r.status_code == 200

    def test_class_create_get(self, authenticated_client):
        r = authenticated_client.get(reverse('bibleclub:bible_class_create'))
        assert r.status_code == 200

    def test_class_create_post(self, authenticated_client, age_group):
        r = authenticated_client.post(reverse('bibleclub:bible_class_create'), {
            'age_group': age_group.pk, 'room': 'Salle B', 'max_capacity': 20,
        })
        assert r.status_code in (200, 302)

    def test_class_detail(self, authenticated_client, bible_class):
        r = authenticated_client.get(
            reverse('bibleclub:class_detail', args=[bible_class.pk])
        )
        assert r.status_code == 200

    def test_monitor_list(self, authenticated_client, monitor):
        r = authenticated_client.get(reverse('bibleclub:monitor_list'))
        assert r.status_code == 200

    def test_monitor_create_get(self, authenticated_client):
        r = authenticated_client.get(reverse('bibleclub:monitor_create'))
        assert r.status_code == 200

    def test_monitor_create_post(self, authenticated_client, bible_class):
        user = User.objects.create_user(
            username='monitor_new', password='password123',
            first_name='Mon', last_name='Iteur',
        )
        r = authenticated_client.post(reverse('bibleclub:monitor_create'), {
            'user': user.pk, 'bible_class': bible_class.pk,
        })
        assert r.status_code in (200, 302)

    def test_monitor_update_get(self, authenticated_client, monitor):
        r = authenticated_client.get(
            reverse('bibleclub:monitor_update', args=[monitor.pk])
        )
        assert r.status_code == 200

    def test_monitor_delete(self, authenticated_client, monitor):
        r = authenticated_client.post(
            reverse('bibleclub:monitor_delete', args=[monitor.pk])
        )
        assert r.status_code in (200, 302)

    def test_children_list(self, authenticated_client, child):
        r = authenticated_client.get(reverse('bibleclub:children_list'))
        assert r.status_code == 200

    def test_child_create_get(self, authenticated_client):
        r = authenticated_client.get(reverse('bibleclub:child_create'))
        assert r.status_code == 200

    def test_child_create_post(self, authenticated_client, age_group):
        r = authenticated_client.post(reverse('bibleclub:child_create'), {
            'first_name': 'Léa', 'last_name': 'Petit',
            'date_of_birth': '2017-09-01', 'gender': 'F',
            'age_group': age_group.pk,
        })
        assert r.status_code in (200, 302)

    def test_child_detail(self, authenticated_client, child):
        r = authenticated_client.get(
            reverse('bibleclub:child_detail', args=[child.pk])
        )
        assert r.status_code == 200

    def test_child_edit_get(self, authenticated_client, child):
        r = authenticated_client.get(
            reverse('bibleclub:child_edit', args=[child.pk])
        )
        assert r.status_code == 200

    def test_child_delete(self, authenticated_client, child):
        r = authenticated_client.post(
            reverse('bibleclub:child_delete', args=[child.pk])
        )
        assert r.status_code in (200, 302)

    def test_session_list(self, authenticated_client, bible_session):
        r = authenticated_client.get(reverse('bibleclub:session_list'))
        assert r.status_code == 200

    def test_session_create_get(self, authenticated_client):
        r = authenticated_client.get(reverse('bibleclub:create_session'))
        assert r.status_code == 200

    def test_session_create_post(self, authenticated_client):
        r = authenticated_client.post(reverse('bibleclub:create_session'), {
            'date': '2026-09-14', 'theme': 'Les psaumes',
        })
        assert r.status_code in (200, 302)

    def test_session_detail(self, authenticated_client, bible_session):
        r = authenticated_client.get(
            reverse('bibleclub:session_detail', args=[bible_session.pk])
        )
        assert r.status_code == 200

    def test_take_attendance_get(self, authenticated_client, bible_session, bible_class):
        r = authenticated_client.get(
            reverse('bibleclub:take_attendance', args=[bible_session.pk, bible_class.pk])
        )
        assert r.status_code == 200

    def test_age_group_list(self, authenticated_client, age_group):
        r = authenticated_client.get(reverse('bibleclub:age_group_list'))
        assert r.status_code == 200

    def test_age_group_create_get(self, authenticated_client):
        r = authenticated_client.get(reverse('bibleclub:age_group_create'))
        assert r.status_code == 200

    def test_age_group_create_post(self, authenticated_client):
        r = authenticated_client.post(reverse('bibleclub:age_group_create'), {
            'name': 'Mini', 'min_age': 3, 'max_age': 5, 'color': '#00CC00',
        })
        assert r.status_code in (200, 302)

    def test_age_group_update_get(self, authenticated_client, age_group):
        r = authenticated_client.get(
            reverse('bibleclub:age_group_update', args=[age_group.pk])
        )
        assert r.status_code == 200

    def test_age_group_delete(self, authenticated_client, age_group):
        r = authenticated_client.post(
            reverse('bibleclub:age_group_delete', args=[age_group.pk])
        )
        assert r.status_code in (200, 302)


# =============================================================================
# INVENTORY views
# =============================================================================

@pytest.mark.django_db
class TestInventoryViews:

    def test_list(self, authenticated_client, equipment):
        r = authenticated_client.get(reverse('inventory:list'))
        assert r.status_code == 200

    def test_create_get(self, authenticated_client):
        r = authenticated_client.get(reverse('inventory:create'))
        assert r.status_code == 200

    def test_create_post(self, authenticated_client, inv_category):
        r = authenticated_client.post(reverse('inventory:create'), {
            'name': 'Table',
            'category': inv_category.pk,
            'quantity': 10,
            'condition': 'new',
        })
        assert r.status_code in (200, 302)

    def test_detail(self, authenticated_client, equipment):
        r = authenticated_client.get(
            reverse('inventory:detail', args=[equipment.pk])
        )
        assert r.status_code == 200

    def test_update_get(self, authenticated_client, equipment):
        r = authenticated_client.get(
            reverse('inventory:update', args=[equipment.pk])
        )
        assert r.status_code == 200

    def test_update_post(self, authenticated_client, equipment, inv_category):
        r = authenticated_client.post(
            reverse('inventory:update', args=[equipment.pk]),
            {'name': 'Chaise modifiée', 'category': inv_category.pk,
             'quantity': 45, 'condition': 'fair'},
        )
        assert r.status_code in (200, 302)

    def test_delete(self, authenticated_client, equipment):
        r = authenticated_client.post(
            reverse('inventory:delete', args=[equipment.pk])
        )
        assert r.status_code in (200, 302)

    def test_category_create_get(self, authenticated_client):
        r = authenticated_client.get(reverse('inventory:category_create'))
        assert r.status_code == 200

    def test_category_create_post(self, authenticated_client):
        r = authenticated_client.post(reverse('inventory:category_create'), {
            'name': 'Électronique',
        })
        assert r.status_code in (200, 302)

    def test_category_update_get(self, authenticated_client, inv_category):
        r = authenticated_client.get(
            reverse('inventory:category_update', args=[inv_category.pk])
        )
        assert r.status_code == 200


# =============================================================================
# FINANCE — Budget views
# =============================================================================

@pytest.mark.django_db
class TestBudgetViews:

    def test_budget_dashboard(self, authenticated_client):
        r = authenticated_client.get(reverse('finance:budget_dashboard'))
        assert r.status_code == 200

    def test_budget_list(self, authenticated_client, budget):
        r = authenticated_client.get(reverse('finance:budget_list'))
        assert r.status_code == 200

    def test_budget_create_get(self, authenticated_client):
        r = authenticated_client.get(reverse('finance:budget_create'))
        assert r.status_code == 200

    def test_budget_create_post(self, authenticated_client):
        r = authenticated_client.post(reverse('finance:budget_create'), {
            'name': 'Budget test', 'year': 2027,
            'total_requested': '5000.00',
        })
        assert r.status_code in (200, 302)

    def test_budget_detail(self, authenticated_client, budget):
        r = authenticated_client.get(
            reverse('finance:budget_detail', args=[budget.pk])
        )
        assert r.status_code == 200

    def test_budget_edit_get(self, authenticated_client, budget):
        r = authenticated_client.get(
            reverse('finance:budget_edit', args=[budget.pk])
        )
        assert r.status_code == 200

    def test_budget_edit_post(self, authenticated_client, budget):
        r = authenticated_client.post(
            reverse('finance:budget_edit', args=[budget.pk]),
            {'name': 'Budget modifié', 'year': 2026,
             'total_requested': '12000.00'},
        )
        assert r.status_code in (200, 302)

    def test_budget_submit(self, authenticated_client, budget):
        r = authenticated_client.post(
            reverse('finance:budget_submit', args=[budget.pk])
        )
        assert r.status_code in (200, 302)

    def test_budget_approve_get(self, authenticated_client, budget):
        budget.status = 'submitted'
        budget.save()
        r = authenticated_client.get(
            reverse('finance:budget_approve_detailed', args=[budget.pk])
        )
        assert r.status_code == 200

    def test_budget_approve_post(self, authenticated_client, budget):
        budget.status = 'submitted'
        budget.save()
        r = authenticated_client.post(
            reverse('finance:budget_approve_detailed', args=[budget.pk]),
            {'total_approved': '9000.00', 'approval_notes': 'OK'},
        )
        assert r.status_code in (200, 302)

    def test_budget_export_excel(self, authenticated_client, budget):
        r = authenticated_client.get(
            reverse('finance:budget_export_excel', args=[budget.pk])
        )
        assert r.status_code == 200

    def test_budget_print(self, authenticated_client, budget):
        r = authenticated_client.get(
            reverse('finance:budget_print', args=[budget.pk])
        )
        assert r.status_code == 200

    def test_budget_list_export_excel(self, authenticated_client):
        r = authenticated_client.get(reverse('finance:budget_list_export_excel'))
        assert r.status_code == 200

    def test_transactions_export_excel(self, authenticated_client):
        r = authenticated_client.get(reverse('finance:transactions_export_excel'))
        assert r.status_code == 200

    def test_budget_request_list(self, authenticated_client, budget_request):
        r = authenticated_client.get(reverse('finance:budget_request_list'))
        assert r.status_code == 200

    def test_budget_request_create_get(self, authenticated_client):
        r = authenticated_client.get(reverse('finance:budget_request_create'))
        assert r.status_code == 200

    def test_budget_request_create_post(self, authenticated_client, budget_category):
        r = authenticated_client.post(reverse('finance:budget_request_create'), {
            'title': 'Achat vidéo',
            'description': 'Besoin caméra',
            'requested_amount': '1200.00',
            'category': budget_category.pk,
            'urgency': 'high',
            'justification': 'Nécessaire pour les retransmissions',
        })
        assert r.status_code in (200, 302)


# =============================================================================
# ACCOUNTS views
# =============================================================================

@pytest.mark.django_db
class TestAccountsViews:

    def test_login_get(self, client):
        r = client.get(reverse('accounts:login'))
        assert r.status_code == 200

    def test_login_post_valid(self, client, admin_user):
        r = client.post(reverse('accounts:login'), {
            'username': 'admin', 'password': 'password123',
        })
        assert r.status_code in (200, 302)

    def test_login_post_invalid(self, client):
        r = client.post(reverse('accounts:login'), {
            'username': 'wrong', 'password': 'wrong',
        })
        assert r.status_code == 200  # form re-rendered

    def test_logout(self, authenticated_client):
        r = authenticated_client.post(reverse('accounts:logout'))
        assert r.status_code in (200, 302)

    def test_profile(self, authenticated_client):
        r = authenticated_client.get(reverse('accounts:profile'))
        assert r.status_code == 200

    def test_profile_post(self, authenticated_client):
        r = authenticated_client.post(reverse('accounts:profile'), {
            'first_name': 'Admin', 'last_name': 'Modifié',
            'email': 'admin@test.com',
        })
        assert r.status_code in (200, 302)

    def test_user_list(self, authenticated_client):
        r = authenticated_client.get(reverse('accounts:user_list'))
        assert r.status_code == 200

    def test_create_user_get(self, authenticated_client):
        r = authenticated_client.get(reverse('accounts:create_user'))
        assert r.status_code == 200

    def test_create_user_post(self, authenticated_client):
        r = authenticated_client.post(reverse('accounts:create_user'), {
            'username': 'new_user_test',
            'email': 'newuser@test.com',
            'first_name': 'Nouveau',
            'last_name': 'Utilisateur',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
            'role': 'membre',
        })
        assert r.status_code in (200, 302)

    def test_user_detail(self, authenticated_client, admin_user):
        r = authenticated_client.get(
            reverse('accounts:user_detail', args=[admin_user.pk])
        )
        assert r.status_code == 200

    def test_user_update_get(self, authenticated_client, extra_user):
        r = authenticated_client.get(
            reverse('accounts:user_update', args=[extra_user.pk])
        )
        assert r.status_code == 200

    def test_user_delete(self, authenticated_client, extra_user):
        r = authenticated_client.post(
            reverse('accounts:user_delete', args=[extra_user.pk])
        )
        assert r.status_code in (200, 302)


# =============================================================================
# IMPORTS views (GET only — file uploads need multipart)
# =============================================================================

@pytest.mark.django_db
class TestImportsViews:

    def test_hub(self, authenticated_client):
        r = authenticated_client.get(reverse('imports:hub'))
        assert r.status_code == 200
        content = r.content.decode()
        assert reverse('finance:import_excel') in content
        assert 'Import Finance Excel' in content
        assert 'Acces disponibles' in content

    def test_list(self, authenticated_client):
        r = authenticated_client.get(reverse('imports:list'))
        assert r.status_code == 200

    def test_create_get(self, authenticated_client):
        r = authenticated_client.get(reverse('imports:create'))
        assert r.status_code == 200

    def test_export_members(self, authenticated_client):
        r = authenticated_client.get(reverse('imports:export_members'))
        assert r.status_code == 200

    def test_export_children(self, authenticated_client):
        r = authenticated_client.get(reverse('imports:export_children'))
        assert r.status_code == 200


# =============================================================================
# WORSHIP — more views
# =============================================================================

@pytest.mark.django_db
class TestWorshipViews:

    def test_service_list(self, authenticated_client):
        r = authenticated_client.get(reverse('worship:service_list'))
        assert r.status_code == 200

    def test_service_create_post(self, authenticated_client, site_cayenne):
        r = authenticated_client.post(reverse('worship:service_create'), {
            'title': 'Culte dimanche',
            'date': '2026-06-07',
            'start_time': '09:00',
            'site': site_cayenne.pk,
        })
        assert r.status_code in (200, 302)

    def test_schedule_list(self, authenticated_client):
        r = authenticated_client.get(reverse('worship:schedule_list'))
        assert r.status_code == 200

    def test_schedule_create_post(self, authenticated_client, site_cayenne):
        r = authenticated_client.post(reverse('worship:schedule_create'), {
            'month': 7, 'year': 2026, 'site': site_cayenne.pk,
        })
        assert r.status_code in (200, 302)

    def test_template_list(self, authenticated_client):
        r = authenticated_client.get(reverse('worship:template_list'))
        assert r.status_code == 200

    def test_template_create_get(self, authenticated_client):
        r = authenticated_client.get(reverse('worship:template_create'))
        assert r.status_code == 200

    def test_template_create_post(self, authenticated_client):
        r = authenticated_client.post(reverse('worship:template_create'), {
            'name': 'Culte standard', 'description': 'Template de base',
            'service_type': 'culte_dominical', 'estimated_duration': 90,
        })
        assert r.status_code in (200, 302)


# =============================================================================
# DASHBOARD views
# =============================================================================

@pytest.mark.django_db
class TestDashboardViews:

    def test_home(self, authenticated_client):
        r = authenticated_client.get(reverse('dashboard:home'))
        assert r.status_code == 200

    def test_stats(self, authenticated_client):
        r = authenticated_client.get(reverse('dashboard:stats'))
        assert r.status_code == 200


# =============================================================================
# RBAC — accès refusé pour membre simple
# =============================================================================

@pytest.mark.django_db
class TestRBACDenials:

    def test_groups_create_denied(self, client, member_user):
        client.force_login(member_user)
        r = client.get(reverse('groups:create'))
        assert r.status_code in (302, 403)

    def test_inventory_create_denied(self, client, member_user):
        client.force_login(member_user)
        r = client.get(reverse('inventory:create'))
        assert r.status_code in (302, 403)

    def test_young_create_denied(self, client, member_user):
        client.force_login(member_user)
        r = client.get(reverse('young:member_create'))
        assert r.status_code in (302, 403)

    def test_transport_create_denied(self, client, member_user):
        client.force_login(member_user)
        r = client.get(reverse('transport:driver_create'))
        assert r.status_code in (302, 403)

    def test_bibleclub_create_denied(self, client, member_user):
        client.force_login(member_user)
        r = client.get(reverse('bibleclub:bible_class_create'))
        assert r.status_code in (302, 403)

    def test_accounts_user_list_denied(self, client, member_user):
        client.force_login(member_user)
        r = client.get(reverse('accounts:user_list'))
        assert r.status_code in (302, 403)

    def test_budget_create_denied(self, client, member_user):
        client.force_login(member_user)
        r = client.get(reverse('finance:budget_create'))
        assert r.status_code in (302, 403)
