# -*- coding: utf-8 -*-
"""
Tests pour le middleware de rate limiting.

Property 4: Login Rate Limiting
Pour toute adresse IP, apres un certain nombre de requetes dans une fenetre de temps,
les requetes suivantes sont bloquees avec une reponse 429.

Validates: Requirements 9.1, 9.2, 9.3, 9.4
"""

import pytest
from django.test import Client, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import HttpResponse
from hypothesis import given, strategies as st, settings as hypothesis_settings, HealthCheck
import time

from apps.core.middleware import RateLimitMiddleware
from apps.core.models import AuditLog

User = get_user_model()


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        username="ratelimit_test_user",
        password="testpass123",
        first_name="RateLimit",
        last_name="Test",
        role="membre"
    )


@pytest.fixture
def admin_test_user(db):
    return User.objects.create_user(
        username="ratelimit_admin_user",
        password="testpass123",
        first_name="Admin",
        last_name="Test",
        role="admin"
    )


@pytest.fixture
def superuser_test(db):
    return User.objects.create_superuser(
        username="ratelimit_superuser",
        password="testpass123",
        first_name="Super",
        last_name="User"
    )


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def middleware():
    def get_response(request):
        return HttpResponse("OK")
    return RateLimitMiddleware(get_response)


class TestRateLimitMiddlewareUnit:
    """Unit tests for rate limiting middleware."""
    
    def test_middleware_initialization(self, middleware):
        assert middleware.max_requests == 1000
        assert middleware.window_seconds == 60
        assert "/static/" in middleware.excluded_paths
    
    def test_excluded_paths_bypass_rate_limiting(self, middleware, request_factory):
        request = request_factory.get("/static/css/style.css")
        request.user = type("AnonymousUser", (), {"is_authenticated": False})()
        response = middleware(request)
        assert response.status_code == 200
    
    def test_get_client_ip_from_remote_addr(self, middleware, request_factory):
        request = request_factory.get("/test/")
        request.META["REMOTE_ADDR"] = "192.168.1.100"
        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.100"
    
    def test_get_client_ip_from_x_forwarded_for(self, middleware, request_factory):
        request = request_factory.get("/test/")
        request.META["HTTP_X_FORWARDED_FOR"] = "10.0.0.1, 192.168.1.1"
        request.META["REMOTE_ADDR"] = "127.0.0.1"
        ip = middleware._get_client_ip(request)
        assert ip == "10.0.0.1"
    
    def test_rate_key_for_anonymous_user(self, middleware, request_factory):
        request = request_factory.get("/test/")
        request.META["REMOTE_ADDR"] = "192.168.1.100"
        request.user = type("AnonymousUser", (), {"is_authenticated": False})()
        key = middleware._get_rate_key(request)
        assert "ip_192.168.1.100" in key
    
    def test_rate_key_for_authenticated_user(self, middleware, request_factory, test_user):
        request = request_factory.get("/test/")
        request.user = test_user
        key = middleware._get_rate_key(request)
        assert f"user_{test_user.id}" in key


class TestRateLimitMiddlewareIntegration:
    """Integration tests for rate limiting middleware."""
    
    @override_settings(RATE_LIMIT_REQUESTS=5, RATE_LIMIT_WINDOW=60)
    def test_requests_under_limit_succeed(self, client, db):
        for i in range(4):
            response = client.get("/app/accounts/login/")
            assert response.status_code == 200
    
    @override_settings(RATE_LIMIT_REQUESTS=5, RATE_LIMIT_WINDOW=60)
    def test_requests_at_limit_blocked(self, client, db):
        for i in range(5):
            response = client.get("/app/accounts/login/")
        response = client.get("/app/accounts/login/")
        assert response.status_code == 429
    
    @override_settings(RATE_LIMIT_REQUESTS=5, RATE_LIMIT_WINDOW=60)
    def test_rate_limit_response_has_retry_after_header(self, client, db):
        for _ in range(5):
            client.get("/app/accounts/login/")
        response = client.get("/app/accounts/login/")
        assert response.status_code == 429
        assert "Retry-After" in response
    
    @override_settings(RATE_LIMIT_REQUESTS=5, RATE_LIMIT_WINDOW=60)
    def test_admin_user_excluded_from_rate_limit(self, client, admin_test_user, db):
        client.force_login(admin_test_user)
        for i in range(10):
            response = client.get("/app/")
            assert response.status_code != 429
    
    @override_settings(RATE_LIMIT_REQUESTS=5, RATE_LIMIT_WINDOW=60)
    def test_superuser_excluded_from_rate_limit(self, client, superuser_test, db):
        client.force_login(superuser_test)
        for i in range(10):
            response = client.get("/app/")
            assert response.status_code != 429
    
    @override_settings(RATE_LIMIT_REQUESTS=5, RATE_LIMIT_WINDOW=60)
    def test_regular_user_is_rate_limited(self, client, test_user, db):
        client.force_login(test_user)
        for _ in range(5):
            client.get("/app/")
        response = client.get("/app/")
        assert response.status_code == 429
    
    @override_settings(RATE_LIMIT_REQUESTS=5, RATE_LIMIT_WINDOW=60)
    def test_rate_limit_creates_audit_log(self, client, db):
        for _ in range(5):
            client.get("/app/accounts/login/")
        client.get("/app/accounts/login/")
        log = AuditLog.objects.filter(
            action=AuditLog.Action.ACCESS_DENIED,
            extra_data__reason="rate_limit_exceeded"
        ).first()
        assert log is not None
    
    @override_settings(RATE_LIMIT_REQUESTS=5, RATE_LIMIT_WINDOW=60)
    def test_ajax_request_returns_json_response(self, client, db):
        for _ in range(5):
            client.get("/app/accounts/login/")
        response = client.get(
            "/app/accounts/login/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        assert response.status_code == 429
        assert response["Content-Type"] == "application/json"
    
    @override_settings(RATE_LIMIT_REQUESTS=5, RATE_LIMIT_WINDOW=60)
    def test_different_ips_have_separate_limits(self, request_factory, middleware, db):
        for ip in ["192.168.1.1", "192.168.1.2"]:
            for _ in range(4):
                request = request_factory.get("/test/")
                request.META["REMOTE_ADDR"] = ip
                request.user = type("AnonymousUser", (), {"is_authenticated": False})()
                response = middleware(request)
                assert response.status_code == 200


@pytest.mark.django_db(transaction=True)
class TestRateLimitPropertyBased:
    """
    Property-based tests for rate limiting middleware.
    
    Feature: security-audit-fixes, Property 4: Login Rate Limiting
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
    """
    
    @given(num_requests=st.integers(min_value=1, max_value=20))
    @hypothesis_settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow])
    def test_rate_limiting_property(self, num_requests):
        """
        Feature: security-audit-fixes, Property 4: Login Rate Limiting
        Property: Pour tout nombre de requetes N, si N >= limite, alors la requete N+1 retourne 429.
        **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
        """
        limit = 5
        cache.clear()
        
        def get_response(request):
            return HttpResponse("OK")
        
        mw = RateLimitMiddleware(get_response)
        mw.max_requests = limit
        mw.window_seconds = 60
        
        factory = RequestFactory()
        unique_ip = f"10.0.{num_requests % 256}.{num_requests}"
        
        last_response = None
        for i in range(num_requests):
            request = factory.get("/test/")
            request.META["REMOTE_ADDR"] = unique_ip
            request.user = type("AnonymousUser", (), {"is_authenticated": False})()
            last_response = mw(request)
        
        if num_requests >= limit:
            request = factory.get("/test/")
            request.META["REMOTE_ADDR"] = unique_ip
            request.user = type("AnonymousUser", (), {"is_authenticated": False})()
            response = mw(request)
            assert response.status_code == 429
        else:
            assert last_response.status_code == 200
    
    @given(role=st.sampled_from(["admin", "membre", "finance", "secretariat"]))
    @hypothesis_settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow])
    def test_admin_exclusion_property(self, role):
        """
        Feature: security-audit-fixes, Property 4: Login Rate Limiting
        Property: Les utilisateurs admin ne sont jamais rate-limited.
        **Validates: Requirements 9.4**
        """
        cache.clear()
        
        user = User.objects.create_user(
            username=f"pbt_user_{role}_{time.time()}",
            password="testpass123",
            role=role
        )
        
        try:
            def get_response(request):
                return HttpResponse("OK")
            
            mw = RateLimitMiddleware(get_response)
            mw.max_requests = 5
            mw.window_seconds = 60
            
            factory = RequestFactory()
            blocked = False
            
            for i in range(10):
                request = factory.get("/test/")
                request.user = user
                response = mw(request)
                if response.status_code == 429:
                    blocked = True
                    break
            
            if role == "admin":
                assert not blocked, "Admin users should never be rate limited"
            else:
                assert blocked, f"Non-admin users ({role}) should be rate limited"
        finally:
            user.delete()


@pytest.mark.django_db
class TestRateLimitEdgeCases:
    """Edge case tests for rate limiting middleware."""
    
    def test_empty_ip_address_handled(self, middleware, request_factory):
        request = request_factory.get("/test/")
        request.META["REMOTE_ADDR"] = ""
        request.user = type("AnonymousUser", (), {"is_authenticated": False})()
        response = middleware(request)
        assert response.status_code == 200
    
    def test_missing_remote_addr_handled(self, middleware, request_factory):
        request = request_factory.get("/test/")
        if "REMOTE_ADDR" in request.META:
            del request.META["REMOTE_ADDR"]
        request.user = type("AnonymousUser", (), {"is_authenticated": False})()
        response = middleware(request)
        assert response.status_code == 200
    
    @override_settings(RATE_LIMIT_REQUESTS=5, RATE_LIMIT_WINDOW=1)
    def test_rate_limit_resets_after_window(self, client, db):
        for _ in range(5):
            client.get("/app/accounts/login/")
        
        response = client.get("/app/accounts/login/")
        assert response.status_code == 429
        
        time.sleep(1.5)
        
        response = client.get("/app/accounts/login/")
        assert response.status_code == 200
