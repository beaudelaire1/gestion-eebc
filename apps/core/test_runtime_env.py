import os
from unittest.mock import patch

from django.test import SimpleTestCase

from gestion_eebc.runtime_env import normalize_runtime_environment


class RuntimeEnvironmentTests(SimpleTestCase):
    def test_maps_legacy_celery_redis_url_when_redis_url_is_missing(self):
        with patch.dict(
            os.environ,
            {'CELERY_BROKER_URL': 'redis://render-key-value:6379/0'},
            clear=True,
        ):
            normalize_runtime_environment()
            self.assertEqual(
                os.environ['REDIS_URL'],
                'redis://render-key-value:6379/0',
            )

    def test_existing_redis_url_has_priority(self):
        with patch.dict(
            os.environ,
            {
                'REDIS_URL': 'rediss://cache.example/0',
                'CELERY_BROKER_URL': 'redis://broker.example/0',
            },
            clear=True,
        ):
            normalize_runtime_environment()
            self.assertEqual(os.environ['REDIS_URL'], 'rediss://cache.example/0')

    def test_non_redis_celery_broker_is_not_used_as_cache(self):
        with patch.dict(
            os.environ,
            {'CELERY_BROKER_URL': 'amqp://rabbitmq.example/'},
            clear=True,
        ):
            normalize_runtime_environment()
            self.assertNotIn('REDIS_URL', os.environ)
