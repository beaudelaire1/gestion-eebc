from html.parser import HTMLParser
from urllib.parse import urlsplit

import pytest
from django.test import override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.accounts.services import AccountsService


class ActivationLinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.activation_url = None

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        attributes = dict(attrs)
        href = attributes.get("href", "")
        if "first-login-password-change" in href:
            self.activation_url = href


@pytest.mark.django_db
@override_settings(SITE_URL="https://gestion.example.test/")
def test_invitation_activation_link_uses_mounted_accounts_route(client, mailoutbox):
    creator = User.objects.create_user(
        username="creator",
        email="creator@example.test",
        password="CreatorPass!2026",
        role="admin",
    )
    invited = User.objects.create_user(
        username="invited",
        email="invited@example.test",
        password="TemporaryPass!2026",
        must_change_password=True,
    )

    sent = AccountsService.send_invitation_email(
        invited, invited.username, "TemporaryPass!2026", creator
    )

    assert sent is True
    assert len(mailoutbox) == 1
    parser = ActivationLinkParser()
    parser.feed(mailoutbox[0].alternatives[0].content)
    activation_url = parser.activation_url
    assert activation_url is not None

    parsed = urlsplit(activation_url)
    assert parsed.scheme == "https"
    assert parsed.netloc == "gestion.example.test"
    assert parsed.path == reverse("accounts:first_login_password_change")
    assert parsed.query.startswith("token=")

    legacy_response = client.get(
        f"/accounts/first-login-password-change/?{parsed.query}"
    )
    assert legacy_response.status_code == 302
    assert legacy_response.url == f"{parsed.path}?{parsed.query}"

    legacy_page = client.get(
        f"/accounts/first-login-password-change/?{parsed.query}", follow=True
    )
    assert legacy_page.status_code == 200
    assert legacy_page.context["user"].pk == invited.pk

    response = client.get(f"{parsed.path}?{parsed.query}")
    assert response.status_code == 200
    assert response.context["user"].pk == invited.pk

    new_password = "ActivatedAccount!2026"
    response = client.post(
        parsed.path,
        {
            "token": parsed.query.removeprefix("token="),
            "new_password1": new_password,
            "new_password2": new_password,
        },
    )
    assert response.status_code == 302
    assert response.url == reverse("dashboard:home")
    invited.refresh_from_db()
    assert invited.must_change_password is False
    assert invited.check_password(new_password)


@pytest.mark.django_db
@override_settings(SITE_URL="https://gestion.example.test/")
def test_password_reset_email_uses_mounted_login_route(mailoutbox):
    admin = User.objects.create_user(
        username="admin",
        email="admin@example.test",
        password="AdminPass!2026",
        role="admin",
    )
    user = User.objects.create_user(
        username="member", email="member@example.test", password="MemberPass!2026"
    )

    sent = AccountsService.send_password_reset_email(
        user, user.username, "TemporaryPass!2026", admin
    )

    assert sent is True
    assert len(mailoutbox) == 1
    html = mailoutbox[0].alternatives[0].content
    assert f'https://gestion.example.test{reverse("accounts:login")}' in html


def test_legacy_login_route_redirects_to_mounted_accounts_route(client):
    response = client.get("/accounts/login/?next=/app/profile/")

    assert response.status_code == 302
    assert response.url == f'{reverse("accounts:login")}?next=/app/profile/'
