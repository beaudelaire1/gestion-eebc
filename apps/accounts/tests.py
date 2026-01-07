from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

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


class UserCreateViewTests(TestCase):
    """Tests pour la vue de création d'utilisateur."""
    
    def setUp(self):
        """Configuration initiale des tests."""
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username='staff',
            password='testpass123',
            is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username='regular',
            password='testpass123',
            is_staff=False
        )
        self.url = reverse('accounts:user_create')
    
    def test_user_create_view_requires_login(self):
        """Test que la vue nécessite une connexion."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_user_create_view_requires_staff(self):
        """Test que seul le staff peut accéder à la vue."""
        self.client.login(username='regular', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
    
    def test_user_create_view_accessible_by_staff(self):
        """Test que le staff peut accéder à la vue."""
        self.client.login(username='staff', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/user_create.html')
    
    def test_user_create_form_valid_submission(self):
        """Test soumission valide du formulaire."""
        self.client.login(username='staff', password='testpass123')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'secure_pass123',
            'password2': 'secure_pass123',
            'role': 'membre',
            'is_active': True,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())
        new_user = User.objects.get(username='newuser')
        self.assertEqual(new_user.email, 'newuser@example.com')
        self.assertEqual(new_user.role, 'membre')
    
    def test_user_create_form_password_mismatch(self):
        """Test avec mots de passe non correspondants."""
        self.client.login(username='staff', password='testpass123')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'secure_pass123',
            'password2': 'different_pass',
            'role': 'membre',
            'is_active': True,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser').exists())


class UserListViewTests(TestCase):
    """Tests pour la vue liste des utilisateurs."""
    
    def setUp(self):
        """Configuration initiale des tests."""
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username='staff',
            password='testpass123',
            is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username='regular',
            password='testpass123',
            is_staff=False
        )
        # Créer quelques utilisateurs supplémentaires
        for i in range(5):
            User.objects.create_user(
                username=f'user{i}',
                password='testpass123',
                first_name=f'User{i}',
                last_name=f'Test{i}'
            )
        self.url = reverse('accounts:user_list')
    
    def test_user_list_view_requires_login(self):
        """Test que la vue nécessite une connexion."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_user_list_view_requires_staff(self):
        """Test que seul le staff peut accéder à la vue."""
        self.client.login(username='regular', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
    
    def test_user_list_view_accessible_by_staff(self):
        """Test que le staff peut accéder à la vue."""
        self.client.login(username='staff', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/user_list.html')
    
    def test_user_list_view_shows_all_users(self):
        """Test que tous les utilisateurs sont affichés."""
        self.client.login(username='staff', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        # 7 utilisateurs au total (staff + regular + 5 créés dans setUp)
        self.assertEqual(len(response.context['users']), 7)

    def test_user_list_search(self):
        """Test de la recherche d'utilisateurs."""
        self.client.login(username='staff', password='testpass123')
        response = self.client.get(self.url + '?search=user0')
        self.assertEqual(response.status_code, 200)

        users = list(response.context['users'])

        # Devrait trouver uniquement user0
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].username, 'user0')

        # Un utilisateur non correspondant (par ex. user1) ne doit pas être présent
        usernames = {user.username for user in users}
        self.assertNotIn('user1', usernames)

    def test_user_list_search(self):
        """Test de la recherche d'utilisateurs."""
        self.client.login(username='staff', password='testpass123')
        response = self.client.get(self.url + '?search=user0')
        self.assertEqual(response.status_code, 200)
        # Devrait trouver uniquement user0
        self.assertEqual(len(response.context['users']), 1)

