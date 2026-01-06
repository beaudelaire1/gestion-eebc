"""
Tests pour le module Departments.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.members.models import Member
from .models import Department

User = get_user_model()


class DepartmentCRUDTestCase(TestCase):
    """Tests pour les opérations CRUD des départements."""
    
    def setUp(self):
        """Configuration des tests."""
        # Créer des utilisateurs de test
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='testpass123',
            role='admin'
        )
        
        self.secretariat_user = User.objects.create_user(
            username='secretariat_test',
            password='testpass123',
            role='secretariat'
        )
        
        self.membre_user = User.objects.create_user(
            username='membre_test',
            password='testpass123',
            role='membre'
        )
        
        # Créer un département de test
        self.department = Department.objects.create(
            name='Test Department',
            description='Department for testing',
            leader=self.admin_user
        )
        
        # Créer des membres de test
        self.member1 = Member.objects.create(
            first_name='John',
            last_name='Doe',
            status=Member.Status.ACTIF,
            email='john@example.com',
            phone='0123456789'
        )
        
        self.member2 = Member.objects.create(
            first_name='Jane',
            last_name='Smith',
            status=Member.Status.ACTIF,
            email='jane@example.com'
        )
        
        self.client = Client()
    
    def test_department_list_view(self):
        """Test de la vue liste des départements."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('departments:list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Department')
    
    def test_department_detail_view(self):
        """Test de la vue détail d'un département."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('departments:detail', kwargs={'pk': self.department.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Department')
    
    def test_department_create_permission_admin(self):
        """Test que les admins peuvent créer des départements."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('departments:create'))
        
        self.assertEqual(response.status_code, 200)
    
    def test_department_create_permission_secretariat(self):
        """Test que le secrétariat peut créer des départements."""
        self.client.force_login(self.secretariat_user)
        response = self.client.get(reverse('departments:create'))
        
        self.assertEqual(response.status_code, 200)
    
    def test_department_create_permission_denied_membre(self):
        """Test que les membres ne peuvent pas créer des départements."""
        self.client.force_login(self.membre_user)
        response = self.client.get(reverse('departments:create'))
        
        # Doit être redirigé (302) car accès refusé
        self.assertEqual(response.status_code, 302)
    
    def test_department_create_post(self):
        """Test de création d'un département via POST."""
        self.client.force_login(self.admin_user)
        
        data = {
            'name': 'New Department',
            'description': 'A new department for testing',
            'leader': self.admin_user.pk
        }
        
        response = self.client.post(reverse('departments:create'), data)
        
        # Doit rediriger vers la page de détail
        self.assertEqual(response.status_code, 302)
        
        # Vérifier que le département a été créé
        new_department = Department.objects.get(name='New Department')
        self.assertEqual(new_department.description, 'A new department for testing')
        self.assertEqual(new_department.leader, self.admin_user)
    
    def test_department_update_permission_admin(self):
        """Test que les admins peuvent modifier des départements."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('departments:update', kwargs={'pk': self.department.pk}))
        
        self.assertEqual(response.status_code, 200)
    
    def test_department_members_management(self):
        """Test de la gestion des membres d'un département."""
        self.client.force_login(self.admin_user)
        
        # Ajouter des membres au département
        data = {
            'members': [self.member1.pk, self.member2.pk]
        }
        
        response = self.client.post(
            reverse('departments:members', kwargs={'pk': self.department.pk}), 
            data
        )
        
        # Doit rediriger vers la page de détail
        self.assertEqual(response.status_code, 302)
        
        # Vérifier que les membres ont été ajoutés
        self.department.refresh_from_db()
        self.assertEqual(self.department.members.count(), 2)
        self.assertIn(self.member1, self.department.members.all())
        self.assertIn(self.member2, self.department.members.all())
    
    def test_department_detail_with_members_stats(self):
        """Test que les statistiques des membres sont correctement affichées."""
        # Ajouter des membres au département
        self.department.members.add(self.member1, self.member2)
        
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('departments:detail', kwargs={'pk': self.department.pk}))
        
        self.assertEqual(response.status_code, 200)
        
        # Vérifier que les statistiques sont dans le contexte
        self.assertIn('stats', response.context)
        stats = response.context['stats']
        
        self.assertEqual(stats['total_members'], 2)
        self.assertEqual(stats['active_members'], 2)
        self.assertEqual(stats['has_phone'], 1)  # Seul member1 a un téléphone
        self.assertEqual(stats['has_email'], 2)  # Les deux ont un email