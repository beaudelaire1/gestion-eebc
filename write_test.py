#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Helper script to write the test file."""

content = '''

class TestRateLimitMiddlewareIntegration:
    @override_settings(RATE_LIMIT_REQUESTS=5, RATE_LIMIT_WINDOW=60)
    def test_requests_under_limit_succeed(self, client, db):
        for i in range(4):
            response = client.get("/app/accounts/login/")
            assert response.status_code == 200, f"Request {i+1} should succeed"
    
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
        retry_after = int(response["Retry-After"])
        assert retry_after > 0
        assert retry_after <= 60
    
    @override_settings(RATE_LIMIT_REQUESTS=5, RATE_LIMIT_WINDOW=60)
    def test_admin_user_excluded_from_rate_limit(self, client, admin_test_user, db):
        client.force_login(admin_test_user)
        for i in range(10):
            response = client.get("/app/")
            assert response.status_code != 429, f"Admin should not be rate limited at request {i+1}"
    
    @override_settings(RATE_LIMIT_REQUESTS=5, RATE_LIMIT_WINDOW=60)
    def test_superuser_excluded_from_rate_limit(self, client, superuser_test, db):
        client.force_login(superuser_test)
        for i in range(10):
            response = client.get("/app/")
            assert response.status_code != 429, f"Superuser should not be rate limited at request {i+1}"
    
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
        assert log.path == "/app/accounts/login/"
    
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
        data = response.json()
        assert "error" in data
        assert "retry_after" in data
    
    @override_settings(RATE_LIMIT_REQUESTS=5, RATE_LIMIT_WINDOW=60)
    def test_different_ips_have_separate_limits(self, request_factory, middleware, db):
        for ip in ["192.168.1.1", "192.168.1.2"]:
            for _ in range(4):
                request = request_factory.get("/test/")
                request.META["REMOTE_ADDR"] = ip
                request.user = type("AnonymousUser", (), {"is_authenticated": False})()
                response = middleware(request)
                assert response.status_code == 200
'''

with open('apps/core/tests/test_rate_limiting.py', 'a', encoding='utf-8') as f:
    f.write(content)
print('Part 3 written')
