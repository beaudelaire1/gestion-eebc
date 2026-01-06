"""
Tests pour la sécurisation de la carte des membres.

Property 7: GPS Obfuscation
Pour tout membre affiché sur la carte, les coordonnées retournées sont décalées
de 50-100 mètres par rapport aux coordonnées réelles, sauf si l'utilisateur est admin.

Validates: Requirements 1.1, 1.2, 26.1, 26.2, 26.3
"""

import pytest
import math
from unittest.mock import patch, MagicMock
from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse

from apps.members.admin_views import (
    obfuscate_coordinates,
    should_obfuscate_for_user,
    members_map_view,
    members_map_data,
)

User = get_user_model()


# =============================================================================
# TESTS POUR obfuscate_coordinates()
# =============================================================================

class TestObfuscateCoordinates:
    """Tests pour la fonction d'obfuscation GPS."""
    
    def test_obfuscate_returns_different_coordinates(self):
        """L'obfuscation retourne des coordonnées différentes de l'original."""
        original_lat, original_lng = 48.8566, 2.3522  # Paris
        
        obfuscated_lat, obfuscated_lng = obfuscate_coordinates(original_lat, original_lng)
        
        # Les coordonnées doivent être différentes
        assert (obfuscated_lat, obfuscated_lng) != (original_lat, original_lng)
    
    def test_obfuscate_distance_within_range(self):
        """
        Property 7: GPS Obfuscation - Distance dans la plage 50-100m
        
        Pour toute coordonnée, le décalage doit être entre 50 et 100 mètres.
        
        **Validates: Requirements 26.1**
        """
        original_lat, original_lng = 48.8566, 2.3522  # Paris
        
        # Tester plusieurs fois pour vérifier la propriété
        for _ in range(100):
            obfuscated_lat, obfuscated_lng = obfuscate_coordinates(
                original_lat, original_lng, 
                min_offset_meters=50, 
                max_offset_meters=100
            )
            
            # Calculer la distance en mètres (formule de Haversine simplifiée)
            distance = self._calculate_distance_meters(
                original_lat, original_lng,
                obfuscated_lat, obfuscated_lng
            )
            
            # La distance doit être entre 50 et 100 mètres (avec une marge de 5%)
            assert 47.5 <= distance <= 105, (
                f"Distance {distance}m hors de la plage 50-100m"
            )
    
    def test_obfuscate_different_each_time(self):
        """L'obfuscation produit des résultats différents à chaque appel."""
        original_lat, original_lng = 48.8566, 2.3522
        
        results = set()
        for _ in range(10):
            result = obfuscate_coordinates(original_lat, original_lng)
            results.add(result)
        
        # Devrait avoir plusieurs résultats différents
        assert len(results) > 1, "L'obfuscation devrait produire des résultats variés"
    
    def test_obfuscate_custom_range(self):
        """L'obfuscation respecte les paramètres min/max personnalisés."""
        original_lat, original_lng = 48.8566, 2.3522
        
        for _ in range(50):
            obfuscated_lat, obfuscated_lng = obfuscate_coordinates(
                original_lat, original_lng,
                min_offset_meters=100,
                max_offset_meters=200
            )
            
            distance = self._calculate_distance_meters(
                original_lat, original_lng,
                obfuscated_lat, obfuscated_lng
            )
            
            # La distance doit être entre 100 et 200 mètres (avec marge)
            assert 95 <= distance <= 210, (
                f"Distance {distance}m hors de la plage 100-200m"
            )
    
    def _calculate_distance_meters(self, lat1, lng1, lat2, lng2):
        """Calcule la distance en mètres entre deux points GPS."""
        # Rayon de la Terre en mètres
        R = 6371000
        
        # Conversion en radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        # Formule de Haversine
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c


# =============================================================================
# TESTS POUR should_obfuscate_for_user()
# =============================================================================

class TestShouldObfuscateForUser:
    """Tests pour la fonction de décision d'obfuscation."""
    
    def test_obfuscate_for_anonymous_user(self):
        """Les utilisateurs anonymes voient des coordonnées obfusquées."""
        anonymous = AnonymousUser()
        assert should_obfuscate_for_user(anonymous) is True
    
    def test_obfuscate_for_none_user(self):
        """Un utilisateur None voit des coordonnées obfusquées."""
        assert should_obfuscate_for_user(None) is True
    
    def test_no_obfuscate_for_superuser(self, db, superuser):
        """
        Property 7: GPS Obfuscation - Admins voient les coordonnées exactes
        
        Les superusers voient les coordonnées exactes.
        
        **Validates: Requirements 26.3**
        """
        assert should_obfuscate_for_user(superuser) is False
    
    def test_no_obfuscate_for_admin(self, db, admin_user):
        """
        Property 7: GPS Obfuscation - Admins voient les coordonnées exactes
        
        Les admins voient les coordonnées exactes.
        
        **Validates: Requirements 26.3**
        """
        assert should_obfuscate_for_user(admin_user) is False
    
    def test_obfuscate_for_secretariat(self, db, secretariat_user):
        """Les utilisateurs secretariat voient des coordonnées obfusquées."""
        assert should_obfuscate_for_user(secretariat_user) is True
    
    def test_obfuscate_for_membre(self, db, membre_user):
        """Les membres voient des coordonnées obfusquées."""
        assert should_obfuscate_for_user(membre_user) is True
    
    def test_obfuscate_for_finance(self, db, finance_user):
        """Les utilisateurs finance voient des coordonnées obfusquées."""
        assert should_obfuscate_for_user(finance_user) is True


# =============================================================================
# TESTS D'ACCÈS À LA CARTE
# =============================================================================

class TestMembersMapAccess:
    """Tests pour l'accès à la carte des membres."""
    
    @pytest.fixture
    def client(self):
        return Client()
    
    def test_map_view_requires_login(self, client, db):
        """
        Property: La carte requiert une authentification.
        
        **Validates: Requirements 1.1**
        """
        response = client.get(reverse('members:map'))
        
        # Devrait rediriger vers login
        assert response.status_code == 302
        assert '/accounts/login/' in response.url or '/login/' in response.url
    
    def test_map_data_requires_login(self, client, db):
        """
        Property: L'API de données de la carte requiert une authentification.
        
        **Validates: Requirements 1.2**
        """
        response = client.get(reverse('members:map_data'))
        
        # Devrait rediriger vers login
        assert response.status_code == 302
    
    def test_map_view_accessible_to_admin(self, client, db, admin_user):
        """
        Property: Les admins peuvent accéder à la carte.
        
        **Validates: Requirements 1.3**
        """
        client.force_login(admin_user)
        response = client.get(reverse('members:map'))
        
        assert response.status_code == 200
    
    def test_map_view_accessible_to_secretariat(self, client, db, secretariat_user):
        """
        Property: Le secrétariat peut accéder à la carte.
        
        **Validates: Requirements 1.3**
        """
        client.force_login(secretariat_user)
        response = client.get(reverse('members:map'))
        
        assert response.status_code == 200
    
    def test_map_view_denied_to_membre(self, client, db, membre_user):
        """
        Property: Les membres ne peuvent pas accéder à la carte.
        
        **Validates: Requirements 1.4**
        """
        client.force_login(membre_user)
        response = client.get(reverse('members:map'))
        
        # Devrait rediriger (accès refusé)
        assert response.status_code == 302
    
    def test_map_view_denied_to_finance(self, client, db, finance_user):
        """
        Property: Les utilisateurs finance ne peuvent pas accéder à la carte.
        
        **Validates: Requirements 1.4**
        """
        client.force_login(finance_user)
        response = client.get(reverse('members:map'))
        
        # Devrait rediriger (accès refusé)
        assert response.status_code == 302
    
    def test_map_data_accessible_to_admin(self, client, db, admin_user):
        """L'API de données est accessible aux admins."""
        client.force_login(admin_user)
        response = client.get(reverse('members:map_data'))
        
        assert response.status_code == 200
    
    def test_map_data_accessible_to_secretariat(self, client, db, secretariat_user):
        """L'API de données est accessible au secrétariat."""
        client.force_login(secretariat_user)
        response = client.get(reverse('members:map_data'))
        
        assert response.status_code == 200
    
    def test_map_data_denied_to_membre(self, client, db, membre_user):
        """L'API de données est refusée aux membres."""
        client.force_login(membre_user)
        response = client.get(reverse('members:map_data'))
        
        # Devrait rediriger (accès refusé)
        assert response.status_code == 302


# =============================================================================
# PROPERTY-BASED TESTS POUR L'OBFUSCATION GPS
# =============================================================================

class TestGPSObfuscationProperty:
    """
    Property 7: GPS Obfuscation
    
    Pour tout membre affiché sur la carte, les coordonnées retournées sont décalées
    de 50-100 mètres par rapport aux coordonnées réelles, sauf si l'utilisateur est admin.
    
    Validates: Requirements 26.1, 26.2, 26.3
    """
    
    @pytest.mark.parametrize("lat,lng", [
        (48.8566, 2.3522),    # Paris
        (45.7640, 4.8357),    # Lyon
        (43.2965, 5.3698),    # Marseille
        (0.0, 0.0),           # Équateur/Méridien
        (-33.8688, 151.2093), # Sydney (hémisphère sud)
        (51.5074, -0.1278),   # Londres (longitude négative)
        (64.1466, -21.9426),  # Reykjavik (haute latitude)
        (-54.8019, -68.3030), # Ushuaia (basse latitude sud)
    ])
    def test_obfuscation_distance_property(self, lat, lng):
        """
        Property 7: Pour toute coordonnée GPS valide, l'obfuscation produit
        un décalage entre 50 et 100 mètres.
        
        **Validates: Requirements 26.1**
        """
        # Tester plusieurs fois pour chaque coordonnée
        for _ in range(20):
            obf_lat, obf_lng = obfuscate_coordinates(lat, lng)
            
            # Calculer la distance
            distance = self._haversine_distance(lat, lng, obf_lat, obf_lng)
            
            # Vérifier la plage (avec marge de 10% pour les erreurs de calcul)
            assert 45 <= distance <= 110, (
                f"Coordonnées ({lat}, {lng}) -> ({obf_lat}, {obf_lng}): "
                f"distance {distance}m hors plage 50-100m"
            )
    
    @pytest.mark.parametrize("user_role,should_obfuscate", [
        ('admin', False),
        ('secretariat', True),
        ('finance', True),
        ('responsable_club', True),
        ('moniteur', True),
        ('responsable_groupe', True),
        ('encadrant', True),
        ('membre', True),
    ])
    def test_obfuscation_by_role_property(self, db, user_role, should_obfuscate):
        """
        Property 7: Seuls les admins voient les coordonnées exactes.
        
        **Validates: Requirements 26.3**
        """
        user = User.objects.create_user(
            username=f'test_{user_role}_obf',
            password='testpass123',
            role=user_role
        )
        
        result = should_obfuscate_for_user(user)
        assert result == should_obfuscate, (
            f"Utilisateur avec rôle {user_role}: "
            f"should_obfuscate devrait être {should_obfuscate}, mais est {result}"
        )
    
    def _haversine_distance(self, lat1, lng1, lat2, lng2):
        """Calcule la distance en mètres entre deux points GPS."""
        R = 6371000  # Rayon de la Terre en mètres
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
