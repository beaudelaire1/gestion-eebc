import pytest
from django.urls import reverse

from apps.core.permissions import can_access_module
from test_factories import UserFactory


pytestmark = pytest.mark.django_db


def test_member_scope_does_not_open_internal_directory():
    user = UserFactory(role="membre")

    assert can_access_module(user, "members") is False
    assert can_access_module(user, "events") is False


def test_multi_role_user_keeps_only_explicit_internal_modules():
    user = UserFactory(role="membre,finance")

    assert can_access_module(user, "finance") is True
    assert can_access_module(user, "members") is False


def test_chauffeur_gets_transport_workspace():
    user = UserFactory(role="chauffeur")

    assert can_access_module(user, "transport") is True
    assert can_access_module(user, "finance") is False


def test_regular_member_cannot_open_member_directory(client):
    user = UserFactory(role="membre")
    client.force_login(user)

    response = client.get(reverse("members:list"))

    assert response.status_code == 302
    assert response.url == reverse("dashboard:home")


def test_finance_cannot_open_member_directory(client):
    user = UserFactory(role="finance")
    client.force_login(user)

    response = client.get(reverse("members:list"))

    assert response.status_code == 302
    assert response.url == reverse("dashboard:home")


def test_encadrant_can_read_member_directory(client):
    user = UserFactory(role="encadrant")
    client.force_login(user)

    response = client.get(reverse("members:list"))

    assert response.status_code == 200


def test_member_cannot_open_family_directory(client):
    user = UserFactory(role="membre")
    client.force_login(user)

    response = client.get(reverse("members:family_list"))

    assert response.status_code == 302
    assert response.url == reverse("dashboard:home")


def test_finance_home_routes_to_finance(client):
    user = UserFactory(role="finance")
    client.force_login(user)

    response = client.get(reverse("dashboard:home"))

    assert response.status_code == 302
    assert response.url == reverse("finance:dashboard")


def test_moniteur_home_routes_to_bibleclub(client):
    user = UserFactory(role="moniteur")
    client.force_login(user)

    response = client.get(reverse("dashboard:home"))

    assert response.status_code == 302
    assert response.url == reverse("bibleclub:home")


def test_member_home_routes_to_public_site(client):
    user = UserFactory(role="membre")
    client.force_login(user)

    response = client.get(reverse("dashboard:home"))

    assert response.status_code == 302
    assert response.url == reverse("public:home")


def test_global_stats_are_admin_only(client):
    user = UserFactory(role="finance")
    client.force_login(user)

    response = client.get(reverse("dashboard:stats"))

    assert response.status_code == 302
    assert response.url == reverse("dashboard:home")


def test_global_search_is_admin_only(client):
    user = UserFactory(role="secretariat")
    client.force_login(user)

    response = client.get(reverse("dashboard:search"), {"q": "test"})

    assert response.status_code == 302
    assert response.url == reverse("dashboard:home")
