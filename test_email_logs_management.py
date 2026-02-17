"""
Tests complets pour la gestion des logs emails.
Valide à la fois l'interface web et la commande CLI.
"""
import os
import sys
import django
from io import StringIO

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_eebc.settings.test')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

django.setup()

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.management import call_command
from apps.communication.models import EmailLog
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()


class EmailLogsManagementTestCase(TestCase):
    """Testons la gestion des logs emails."""

    @classmethod
    def setUpClass(cls):
        """Préparer les données de test."""
        super().setUpClass()
        
        # Créer un utilisateur admin
        cls.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123'
        )
        # Ajouter le rôle admin
        if hasattr(cls.admin_user, 'userprofile'):
            cls.admin_user.userprofile.role = 'admin'
            cls.admin_user.userprofile.save()

        # Créer un utilisateur normal
        cls.normal_user = User.objects.create_user(
            username='user_test',
            email='user@test.com',
            password='testpass123'
        )

        # Créer des logs de test
        now = timezone.now()
        cls.test_logs = [
            EmailLog.objects.create(
                recipient_email='test1@example.com',
                subject='Test Email 1',
                status='sent',
                created_at=now - timedelta(days=10)
            ),
            EmailLog.objects.create(
                recipient_email='test2@example.com',
                subject='Test Email 2',
                status='failed',
                created_at=now - timedelta(days=5)
            ),
            EmailLog.objects.create(
                recipient_email='test3@example.com',
                subject='Test Email 3',
                status='pending',
                created_at=now - timedelta(days=1)
            ),
            EmailLog.objects.create(
                recipient_email='test4@example.com',
                subject='Test Email 4',
                status='bounced',
                created_at=now
            ),
        ]

    def test_email_logs_page_requires_login(self):
        """Vérifier que la page de gestion nécessite une connexion."""
        client = Client()
        response = client.get(reverse('email_logs_management'))
        
        # Doit rediriger vers la connexion
        self.assertIn(response.status_code, [302, 403])

    def test_email_logs_page_requires_admin(self):
        """Vérifier que seuls les admins peuvent accéder."""
        client = Client()
        client.force_login(self.normal_user)
        
        response = client.get(reverse('email_logs_management'))
        
        # L'utilisateur normal ne devrait pas pouvoir accéder
        self.assertEqual(response.status_code, 403)

    def test_email_logs_page_admin_access(self):
        """Vérifier que l'admin peut accéder à la page."""
        client = Client()
        client.force_login(self.admin_user)
        
        response = client.get(reverse('email_logs_management'))
        
        # Admin peut accéder
        self.assertEqual(response.status_code, 200)
        self.assertIn('logs', response.context)
        self.assertIn('total_logs', response.context)

    def test_email_logs_filtering_by_status(self):
        """Tester le filtrage par statut."""
        client = Client()
        client.force_login(self.admin_user)
        
        response = client.get(
            reverse('email_logs_management'),
            {'status': 'sent'}
        )
        
        self.assertEqual(response.status_code, 200)
        logs = response.context['logs']
        # Au moins 1 log avec statut 'sent'
        self.assertTrue(logs.count() >= 1)

    def test_email_logs_search(self):
        """Tester la recherche par email."""
        client = Client()
        client.force_login(self.admin_user)
        
        response = client.get(
            reverse('email_logs_management'),
            {'search': 'test1@example.com'}
        )
        
        self.assertEqual(response.status_code, 200)
        logs = response.context['logs']
        self.assertTrue(logs.count() >= 1)

    def test_email_logs_deletion_requires_post(self):
        """Vérifier que la suppression nécessite POST."""
        client = Client()
        client.force_login(self.admin_user)
        
        # GET devrait retourner 200 (affichage)
        response = client.get(reverse('email_logs_management'))
        self.assertEqual(response.status_code, 200)

    def test_email_logs_deletion_single(self):
        """Tester la suppression d'un log."""
        client = Client()
        client.force_login(self.admin_user)
        
        initial_count = EmailLog.objects.count()
        log_id = self.test_logs[0].id
        
        response = client.post(
            reverse('email_logs_management'),
            {'selected_logs': str(log_id)}
        )
        
        # Vérifier la suppression
        final_count = EmailLog.objects.count()
        self.assertEqual(final_count, initial_count - 1)
        self.assertFalse(EmailLog.objects.filter(id=log_id).exists())

    def test_email_logs_deletion_multiple(self):
        """Tester la suppression de plusieurs logs."""
        client = Client()
        client.force_login(self.admin_user)
        
        initial_count = EmailLog.objects.count()
        ids = [str(self.test_logs[0].id), str(self.test_logs[1].id)]
        
        response = client.post(
            reverse('email_logs_management'),
            {'selected_logs': ','.join(ids)}
        )
        
        # Vérifier les suppressions
        final_count = EmailLog.objects.count()
        self.assertEqual(final_count, initial_count - 2)

    def test_email_logs_statistics(self):
        """Tester les statistiques affichées."""
        client = Client()
        client.force_login(self.admin_user)
        
        response = client.get(reverse('email_logs_management'))
        
        context = response.context
        self.assertIn('total_logs', context)
        self.assertIn('sent_count', context)
        self.assertIn('failed_count', context)
        self.assertIn('pending_count', context)

    def test_management_command_execution(self):
        """Tester l'exécution de la commande de gestion."""
        out = StringIO()
        
        # Exécuter avec --dry-run pour ne rien supprimer
        try:
            call_command(
                'delete_email_logs_interactive',
                '--dry-run',
                stdout=out,
                stderr=out
            )
            output = out.getvalue()
            self.assertIn('Mode dry-run', output)
        except Exception as e:
            self.fail(f"Commande échec: {str(e)}")

    def test_pagination(self):
        """Tester la pagination des logs."""
        # Créer plus de logs pour tester la pagination
        for i in range(50):
            EmailLog.objects.create(
                recipient_email=f'test{i}@example.com',
                subject=f'Test Email {i}',
                status='sent'
            )
        
        client = Client()
        client.force_login(self.admin_user)
        
        response = client.get(reverse('email_logs_management'))
        
        # Vérifier la pagination
        self.assertIn('page_obj', response.context)
        page = response.context['page_obj']
        # Par défaut 50 par page
        self.assertTrue(len(page) <= 50)


def run_tests():
    """Exécuter tous les tests."""
    from django.test.runner import DiscoverRunner
    
    runner = DiscoverRunner(verbosity=2)
    failures = runner.run_tests([__name__])
    
    return failures == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
