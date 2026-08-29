from unittest.mock import patch
import math

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.core.models import Site
from apps.members.geocoding import build_address_key, geocode_address, geocode_address_with_metadata
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

    @patch('apps.members.geocoding.requests.get')
    def test_neighboring_numbers_use_same_street_anchor(self, mock_get):
        mock_get.side_effect = [
            MockResponse({
                'features': [{
                    'geometry': {'coordinates': [-52.305371, 4.919905]},
                    'properties': {
                        'score': 0.92,
                        'type': 'housenumber',
                        'city': 'Cayenne',
                        'postcode': '97300',
                        'label': '1482 Route de Troubiran 97300 Cayenne',
                    },
                }]
            }),
            MockResponse({
                'features': [{
                    'geometry': {'coordinates': [-52.305903, 4.922092]},
                    'properties': {
                        'score': 0.72,
                        'type': 'street',
                        'city': 'Cayenne',
                        'postcode': '97300',
                        'label': 'Route de Troubiran 97300 Cayenne',
                    },
                }]
            }),
        ]

        first = geocode_address_with_metadata('1482 ROUTE DE TROUBIRAN', 'Cayenne', '97300')
        second = geocode_address_with_metadata('1483 ROUTE DE TROUBIRAN', 'Cayenne', '97300')

        self.assertEqual(first['precision'], 'housenumber')
        self.assertEqual(second['precision'], 'same-street-anchor')
        self.assertLess(_distance_meters(first['coords'], second['coords']), 10)


def _distance_meters(coords_a, coords_b):
    radius_meters = 6371000
    lat_a, lon_a = map(math.radians, coords_a)
    lat_b, lon_b = map(math.radians, coords_b)
    delta_lat = lat_b - lat_a
    delta_lon = lon_b - lon_a
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * radius_meters * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))
