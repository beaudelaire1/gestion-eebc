"""Le prévisionnel budgétaire doit être administrable.

`BudgetForecast` et `ForecastLine` n'étaient enregistrés dans aucun admin : les
données saisies — dont les jeux de test — étaient invisibles et impossibles à
supprimer depuis l'interface d'administration.
"""

import pytest
from django.contrib.admin.sites import site
from django.urls import reverse

from apps.accounts.models import User
from apps.finance.models import BudgetForecast, ForecastLine

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client_logged(client):
    user = User.objects.create_superuser(
        username='admin-forecast',
        email='admin-forecast@example.test',
        password='SecurePass!2026',
    )
    client.force_login(user)
    return client


def test_forecast_models_are_registered():
    assert BudgetForecast in site._registry
    assert ForecastLine in site._registry


def test_forecast_changelists_render(admin_client_logged):
    forecast = BudgetForecast.objects.create(name='Prévisionnel test', year=2026)
    ForecastLine.objects.create(
        forecast=forecast,
        label='Dons test',
        line_type=ForecastLine.LineType.INCOME,
        jan=100,
    )

    for url_name in (
        'admin:finance_budgetforecast_changelist',
        'admin:finance_forecastline_changelist',
    ):
        response = admin_client_logged.get(reverse(url_name))
        assert response.status_code == 200, url_name

    detail = admin_client_logged.get(
        reverse('admin:finance_budgetforecast_change', args=[forecast.pk])
    )
    assert detail.status_code == 200
