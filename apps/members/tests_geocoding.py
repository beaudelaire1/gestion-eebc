from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.core.models import Site
from apps.members.geocoding import build_address_key, geocode_address
from apps.members.models import GeocodedAddress, Member


class MockResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class GeocodingConsistencyTests(TestCase):
    def setUp(self):
        geocode_address.cache_clear()
        GeocodedAddress.objects.all().delete()

    def test_address_key_is_stable_for_variants(self):
        key1 = build_address_key(" 12 rue de l'Église ", city="Cayenne", postal_code="97300")
        key2 = build_address_key("12 RUE DE L EGLISE", city="  CAYENNE  ", postal_code="97300.0")
        self.assertEqual(key1, key2)

    @patch('apps.members.geocoding.requests.get')
    def test_geocode_cache_deduplicates_same_address(self, mock_get):
        mock_get.return_value = MockResponse([
            {'lat': '4.9225001', 'lon': '-52.3058001', 'importance': 0.72, 'place_rank': 30, 'type': 'house'}
        ])

        coords_1 = geocode_address("12 rue X", city="Cayenne", postal_code="97300")
        coords_2 = geocode_address("12 RUE X", city="cayenne", postal_code="97300.0")

        self.assertEqual(coords_1, coords_2)
        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(GeocodedAddress.objects.count(), 1)

    @patch('apps.members.geocoding.requests.get')
    def test_map_data_groups_same_canonical_address(self, mock_get):
        mock_get.return_value = MockResponse([
            {'lat': '4.9225002', 'lon': '-52.3058002', 'importance': 0.75, 'place_rank': 30, 'type': 'house'}
        ])

        user_model = get_user_model()
        admin = user_model.objects.create_user(username='geo_admin', password='pass1234', role='admin')

        site = Site.objects.create(code='CAB', name='Cabassou', city='Cayenne', is_active=True)
        Member.objects.create(first_name='Jean', last_name='A', status='actif', site=site, address='12 rue x', city='Cayenne', postal_code='97300')
        Member.objects.create(first_name='Marie', last_name='B', status='actif', site=site, address='12 RUE X', city='cayenne', postal_code='97300.0')

        client = Client()
        client.force_login(admin)

        response = client.get(reverse('members:map_data'))
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        member_points = payload['members']
        self.assertEqual(len(member_points), 2)

        keys = {m['location_key'] for m in member_points}
        coords = {(round(m['lat'], 6), round(m['lng'], 6)) for m in member_points}

        self.assertEqual(len(keys), 1)
        self.assertEqual(len(coords), 1)
