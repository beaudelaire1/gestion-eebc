"""Regression tests for Render/Cloudflare client-IP resolution."""

from django.test import RequestFactory, override_settings

from apps.core.security import get_trusted_client_ip


def test_render_cf_connecting_ip_is_used_when_explicitly_configured():
    request = RequestFactory().get(
        '/',
        REMOTE_ADDR='10.0.0.12',
        HTTP_CF_CONNECTING_IP='203.0.113.42',
        HTTP_X_FORWARDED_FOR='198.51.100.10, 10.0.0.12',
    )

    with override_settings(
        TRUSTED_CLIENT_IP_HEADER='HTTP_CF_CONNECTING_IP',
        TRUSTED_PROXY_IPS=[],
    ):
        assert get_trusted_client_ip(request) == '203.0.113.42'


def test_render_trusted_header_rejects_multiple_addresses():
    request = RequestFactory().get(
        '/',
        REMOTE_ADDR='10.0.0.12',
        HTTP_CF_CONNECTING_IP='203.0.113.42, 198.51.100.5',
        HTTP_X_FORWARDED_FOR='198.51.100.10',
    )

    with override_settings(
        TRUSTED_CLIENT_IP_HEADER='HTTP_CF_CONNECTING_IP',
        TRUSTED_PROXY_IPS=[],
    ):
        assert get_trusted_client_ip(request) == '10.0.0.12'


def test_invalid_render_trusted_header_falls_back_to_remote_address():
    request = RequestFactory().get(
        '/',
        REMOTE_ADDR='10.0.0.12',
        HTTP_CF_CONNECTING_IP='not-an-ip',
    )

    with override_settings(
        TRUSTED_CLIENT_IP_HEADER='HTTP_CF_CONNECTING_IP',
        TRUSTED_PROXY_IPS=[],
    ):
        assert get_trusted_client_ip(request) == '10.0.0.12'
