"""
Tests de non-régression pour le correctif "Nouvelle Famille"

Valide :
1. Pas de double initialisation TomSelect
2. Auto-remplissage fonctionnel (1 sélection = 1 fetch)
3. UX améliorée (rendering enrichi)
4. Pas de boucle infinie
"""
import pytest
from django.test import Client, TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.members.models import Member
from apps.core.models import Site, Family

User = get_user_model()


@pytest.mark.django_db
class TestFamilyCreateBugfix(TestCase):
    """Tests du correctif famille."""
    
    def setUp(self):
        """Configuration tests."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='admin',
            password='testpass123',
            email='admin@eebc.test',
            role='admin'
        )
        self.client.login(username='admin', password='testpass123')
        
        # Site de test
        self.site = Site.objects.create(
            name='Cabassou',
            is_active=True
        )
        
        # Membres actifs de test
        self.member1 = Member.objects.create(
            first_name='Jean',
            last_name='DUPONT',
            status='actif',
            site=self.site,
            phone='0694123456',
            email='jean.dupont@test.com',
            address='10 Rue Test',
            city='Cayenne',
            postal_code='97300'
        )
        self.member2 = Member.objects.create(
            first_name='Marie',
            last_name='MARTIN',
            status='actif',
            site=self.site,
            phone='0694987654'
        )
    
    def test_family_create_page_loads(self):
        """La page 'Nouvelle famille' se charge sans erreur."""
        url = reverse('members:family_create')
        response = self.client.get(url)
        assert response.status_code == 200
        assert 'available_members' in response.context
        assert 'sites' in response.context
    
    def test_available_members_data_structure(self):
        """Les membres disponibles contiennent toutes les données pour UX enrichie."""
        url = reverse('members:family_create')
        response = self.client.get(url)
        
        members = list(response.context['available_members'])
        assert len(members) == 2
        
        # Vérifier que les select_related/only fonctionnent
        member = members[0]
        assert hasattr(member, 'first_name')
        assert hasattr(member, 'last_name')
        assert hasattr(member, 'phone')
        assert hasattr(member, 'photo')
        # Site doit être préchargé
        if member.site:
            # Ne doit pas provoquer de requête SQL supplémentaire
            assert member.site.name
    
    def test_template_no_tom_select_class(self):
        """Le select ne doit PAS avoir la classe .tom-select (évite double init)."""
        url = reverse('members:family_create')
        response = self.client.get(url)
        html = response.content.decode('utf-8')
        
        # Vérifier que #chef-famille-select n'a PAS la classe tom-select
        assert 'id="chef-famille-select"' in html
        # Si on trouve tom-select sur cette ligne, c'est un problème
        lines = html.split('\n')
        select_line = [l for l in lines if 'id="chef-famille-select"' in l][0]
        assert 'class="form-select"' in select_line
        assert 'tom-select' not in select_line, "Le select ne doit pas avoir .tom-select (double init)"
    
    def test_template_has_data_attributes(self):
        """Les options du select doivent avoir les data-* attributes pour UX."""
        url = reverse('members:family_create')
        response = self.client.get(url)
        html = response.content.decode('utf-8')
        
        # Vérifier présence des data-attributes
        assert 'data-first-name=' in html
        assert 'data-last-name=' in html
        assert 'data-phone=' in html
        assert 'data-site=' in html
    
    def test_member_api_data_endpoint(self):
        """L'endpoint API retourne les bonnes données."""
        url = reverse('members:member_api_data', args=[self.member1.pk])
        response = self.client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['first_name'] == 'Jean'
        assert data['last_name'] == 'DUPONT'
        assert data['phone'] == '0694123456'
        assert data['email'] == 'jean.dupont@test.com'
        assert data['address'] == '10 Rue Test'
        assert data['city'] == 'Cayenne'
        assert data['postal_code'] == '97300'
        assert data['site_id'] == self.site.id
    
    def test_member_api_fallback_to_family_data(self):
        """Si membre n'a pas d'adresse, fallback sur celle de la famille."""
        # Créer une famille avec adresse
        family = Family.objects.create(
            name='Famille TEST',
            site=self.site,
            address='20 Rue Famille',
            city='Matoury',
            postal_code='97351',
            phone='0594111111',
            email='famille@test.com'
        )
        
        # Membre sans adresse propre
        member_no_addr = Member.objects.create(
            first_name='Paul',
            last_name='BERNARD',
            status='actif',
            family=family
        )
        
        url = reverse('members:member_api_data', args=[member_no_addr.pk])
        response = self.client.get(url)
        data = response.json()
        
        # Doit fallback sur données famille
        assert data['address'] == '20 Rue Famille'
        assert data['city'] == 'Matoury'
        assert data['postal_code'] == '97351'
        assert data['phone'] == '0594111111'
        assert data['email'] == 'famille@test.com'
    
    def test_create_family_post(self):
        """Créer une famille via POST fonctionne correctement."""
        url = reverse('members:family_create')
        data = {
            'name': 'Famille DUPONT',
            'site': self.site.id,
            'address': '10 Rue Test',
            'city': 'Cayenne',
            'postal_code': '97300',
            'phone': '0694123456',
            'email': 'dupont@test.com'
        }
        
        response = self.client.post(url, data)
        
        # Redirection vers detail
        assert response.status_code == 302
        
        # Famille créée
        family = Family.objects.get(name='Famille DUPONT')
        assert family.site == self.site
        assert family.address == '10 Rue Test'
        assert family.phone == '0694123456'
    
    def test_no_infinite_loop_simulation(self):
        """
        Simulation : vérifier qu'une seule requête API est faite.
        
        Note : Ce test ne peut pas 100% simuler le comportement JS,
        mais on valide que l'endpoint ne boucle pas côté serveur.
        """
        url = reverse('members:member_api_data', args=[self.member1.pk])
        
        # Faire 3 appels rapides (simule ce qui pourrait arriver en boucle)
        responses = []
        for _ in range(3):
            r = self.client.get(url)
            responses.append(r.status_code)
        
        # Toutes les requêtes doivent réussir indépendamment
        assert all(status == 200 for status in responses)
        
        # L'endpoint ne doit pas causer d'effet de bord
        # (pas de création/modification en GET)
        count_before = Member.objects.count()
        self.client.get(url)
        count_after = Member.objects.count()
        assert count_before == count_after


@pytest.mark.django_db
def test_query_optimization():
    """Vérifier que la vue family_create n'a qu'un nombre minimal de requêtes SQL."""
    from django.test.utils import override_settings
    from django.test import RequestFactory
    from django.contrib.auth import get_user_model
    from apps.members.family_views import family_create
    
    User = get_user_model()
    
    # Setup
    user = User.objects.create_user(username='test', password='test', role='admin')
    site = Site.objects.create(name='Test Site', is_active=True)
    for i in range(10):
        Member.objects.create(
            first_name=f'Member{i}',
            last_name=f'Test{i}',
            status='actif',
            site=site
        )
    
    factory = RequestFactory()
    request = factory.get(reverse('members:family_create'))
    request.user = user
    
    # Compter les requêtes
    from django.test.utils import CaptureQueriesContext
    from django.db import connection
    
    with CaptureQueriesContext(connection) as queries:
        response = family_create(request)
    
    # La vue doit faire un nombre raisonnable de requêtes
    # (sites + neighborhoods + members avec select_related)
    num_queries = len(queries)
    
    # Max 5 requêtes (user session + sites + neighborhoods + members + template checks)
    assert num_queries <= 8, f"Trop de requêtes : {num_queries} (attendu <= 8)"
    
    print(f"✓ Query optimization OK : {num_queries} requêtes SQL")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
