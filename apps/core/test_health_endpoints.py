from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase


class HealthEndpointTests(SimpleTestCase):
    def test_platform_ping_is_dependency_free(self):
        with (
            patch(
                "apps.core.health_views._check_database",
                side_effect=AssertionError("ping must not query the database"),
            ),
            patch(
                "apps.core.health_views._check_cache",
                side_effect=AssertionError("ping must not query the cache"),
            ),
            patch(
                "apps.core.health_views._check_celery",
                side_effect=AssertionError("ping must not query Celery"),
            ),
            patch(
                "apps.core.middleware.cache.get",
                side_effect=AssertionError("ping must not query middleware cache"),
            ),
            patch(
                "apps.core.middleware.cache.set",
                side_effect=AssertionError("ping must not update middleware cache"),
            ),
        ):
            response = self.client.get("/healthz/ping/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_render_blueprint_uses_the_declared_ping_route(self):
        blueprint = (Path(settings.BASE_DIR) / "render.yaml").read_text(
            encoding="utf-8"
        )

        self.assertIn("healthCheckPath: /healthz/ping/", blueprint)
