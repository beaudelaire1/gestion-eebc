"""
Tests pour le module Worship.

Couvre : WorshipService, ServiceRole (workflow), is_complete.
"""
import pytest
from datetime import date, time, timedelta

from django.utils import timezone

from apps.worship.models import WorshipService, ServiceRole
from test_factories import (
    SiteFactory,
    UserFactory,
    MemberFactory,
    EventFactory,
    EventCategoryFactory,
)


@pytest.fixture
def worship_event(db):
    """Crée un Event utilisable pour un WorshipService."""
    site = SiteFactory()
    cat = EventCategoryFactory(name="Culte")
    return EventFactory(
        site=site,
        category=cat,
        title="Culte dominical",
        start_date=date.today() + timedelta(days=7),
        start_time=time(9, 30),
    )


@pytest.fixture
def worship_service(worship_event, db):
    """Crée un WorshipService de test."""
    user = UserFactory(role='pasteur')
    return WorshipService.objects.create(
        event=worship_event,
        service_type=WorshipService.ServiceType.CULTE_DOMINICAL,
        theme="La grâce de Dieu",
        bible_text="Éphésiens 2:8-10",
        sermon_title="Sauvés par grâce",
        created_by=user,
    )


# =============================================================================
# WorshipService
# =============================================================================

class TestWorshipService:
    """Tests pour le modèle WorshipService."""

    def test_creation(self, worship_service):
        """Un service de culte peut être créé."""
        assert worship_service.pk is not None
        assert worship_service.service_type == 'culte_dominical'

    def test_date_property(self, worship_service):
        """La propriété date renvoie la date de l'événement."""
        assert worship_service.date == worship_service.event.start_date

    def test_start_time_property(self, worship_service):
        """La propriété start_time renvoie l'heure de l'événement."""
        assert worship_service.start_time == worship_service.event.start_time

    def test_str_representation(self, worship_service):
        """__str__ contient le type de service."""
        s = str(worship_service)
        assert 'Culte dominical' in s

    def test_is_complete_false_no_roles(self, worship_service):
        """Un service sans rôles essentiels n'est pas complet."""
        assert worship_service.is_complete is False

    def test_is_complete_true_with_essential_roles(self, worship_service):
        """Un service avec prédicateur et dirigeant confirmés est complet."""
        member1 = MemberFactory(site=worship_service.event.site)
        member2 = MemberFactory(site=worship_service.event.site)

        ServiceRole.objects.create(
            service=worship_service,
            role=ServiceRole.RoleType.PREDICATEUR,
            member=member1,
            status=ServiceRole.Status.CONFIRME,
        )
        ServiceRole.objects.create(
            service=worship_service,
            role=ServiceRole.RoleType.DIRIGEANT,
            member=member2,
            status=ServiceRole.Status.CONFIRME,
        )

        assert worship_service.is_complete is True

    def test_is_complete_false_pending_roles(self, worship_service):
        """Un service avec rôles en attente n'est pas complet."""
        member = MemberFactory(site=worship_service.event.site)

        ServiceRole.objects.create(
            service=worship_service,
            role=ServiceRole.RoleType.PREDICATEUR,
            member=member,
            status=ServiceRole.Status.EN_ATTENTE,
        )

        assert worship_service.is_complete is False


# =============================================================================
# ServiceRole
# =============================================================================

class TestServiceRole:
    """Tests pour le workflow des rôles de service."""

    def test_default_status_en_attente(self, worship_service):
        """Le statut par défaut est EN_ATTENTE."""
        member = MemberFactory(site=worship_service.event.site)
        role = ServiceRole.objects.create(
            service=worship_service,
            role=ServiceRole.RoleType.CHORISTE,
            member=member,
        )
        assert role.status == ServiceRole.Status.EN_ATTENTE

    def test_confirm_role(self, worship_service):
        """Un rôle peut être confirmé."""
        member = MemberFactory(site=worship_service.event.site)
        role = ServiceRole.objects.create(
            service=worship_service,
            role=ServiceRole.RoleType.SONORISATION,
            member=member,
        )
        role.status = ServiceRole.Status.CONFIRME
        role.confirmed_at = timezone.now()
        role.save()

        role.refresh_from_db()
        assert role.status == ServiceRole.Status.CONFIRME
        assert role.confirmed_at is not None

    def test_decline_role(self, worship_service):
        """Un rôle peut être décliné."""
        member = MemberFactory(site=worship_service.event.site)
        role = ServiceRole.objects.create(
            service=worship_service,
            role=ServiceRole.RoleType.ACCUEIL,
            member=member,
        )
        role.status = ServiceRole.Status.DECLINE
        role.save()

        role.refresh_from_db()
        assert role.status == ServiceRole.Status.DECLINE

    def test_replace_role(self, worship_service):
        """Un rôle peut être remplacé."""
        member1 = MemberFactory(site=worship_service.event.site)
        member2 = MemberFactory(site=worship_service.event.site)

        role = ServiceRole.objects.create(
            service=worship_service,
            role=ServiceRole.RoleType.LECTURE,
            member=member1,
            status=ServiceRole.Status.DECLINE,
        )
        role.status = ServiceRole.Status.REMPLACE
        role.replaced_by = member2
        role.save()

        role.refresh_from_db()
        assert role.status == ServiceRole.Status.REMPLACE
        assert role.replaced_by == member2

    def test_str_representation(self, worship_service):
        """__str__ contient le rôle."""
        member = MemberFactory(site=worship_service.event.site)
        role = ServiceRole.objects.create(
            service=worship_service,
            role=ServiceRole.RoleType.PREDICATEUR,
            member=member,
        )
        s = str(role)
        assert 'Prédicateur' in s or 'predicateur' in s.lower()
