from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class UserModelTests(TestCase):
    """Tests pour le modele User."""
    
    def test_create_user(self):
        """Test creation d'un utilisateur."""
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role='membre'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.role, 'membre')
        self.assertTrue(user.check_password('testpass123'))
    
    def test_user_roles(self):
        """Test des proprietes de role."""
        admin = User.objects.create_user(
            username='admin_test',
            password='test123',
            role='admin'
        )
        self.assertTrue(admin.is_admin)
        
        moniteur = User.objects.create_user(
            username='moniteur_test',
            password='test123',
            role='moniteur'
        )
        self.assertTrue(moniteur.is_moniteur)
        self.assertFalse(moniteur.is_admin)
    
    def test_user_str(self):
        """Test representation string."""
        user = User.objects.create_user(
            username='testuser',
            password='test123',
            first_name='Jean',
            last_name='Dupont'
        )
        self.assertEqual(str(user), 'Jean Dupont')

