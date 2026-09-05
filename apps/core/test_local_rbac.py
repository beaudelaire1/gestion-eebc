"""Contrôle de rôle local sur les écrans de gestion.

Ces vues n'étaient protégées que par OrdinaryMemberAccessMiddleware, qui ne
filtre que les comptes sans rôle : tout compte portant un rôle — un chauffeur,
un moniteur — atteignait la composition d'e-mails, les exports de données
personnelles ou les fiches familles. Le contrôle appartient à la vue.
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


pytestmark = pytest.mark.django_db


@pytest.fixture
def driver_client(client):
    """Compte privilégié, donc hors de portée du middleware, mais sans rapport."""
    user = get_user_model().objects.create_user(
        username='chauffeur.jean',
        email='chauffeur@example.test',
        password='Driver-pass-123!',
        role='chauffeur',
    )
    client.force_login(user)
    return client


@pytest.fixture
def admin_client(client):
    user = get_user_model().objects.create_user(
        username='admin.eebc',
        email='admin@example.test',
        password='Admin-pass-123!',
        role='admin',
    )
    client.force_login(user)
    return client


MANAGEMENT_URLS = [
    'communication:email_compose',
    'communication:email_logs',
    'communication:sms_logs',
    'communication:email_smtp_diagnostic',
    'imports:export_members',
    'imports:export_children',
    'imports:export_young_members',
    'members:family_list',
    'groups:create',
    'departments:create',
    'campaigns:list',
    'core:site_list',
    'documents:generated_create',
]


@pytest.mark.parametrize('url_name', MANAGEMENT_URLS)
def test_unrelated_role_cannot_open_management_screens(driver_client, url_name):
    """role_required refuse par redirection vers le tableau de bord."""
    response = driver_client.get(reverse(url_name))

    assert response.status_code == 302
    assert response.url == reverse('dashboard:home')


@pytest.mark.parametrize('url_name', MANAGEMENT_URLS)
def test_admin_still_opens_management_screens(admin_client, url_name):
    assert admin_client.get(reverse(url_name)).status_code == 200
