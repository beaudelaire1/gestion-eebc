"""
Tests pour les services d'email.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core import mail
from django.contrib.auth import get_user_model

from apps.communication.models import EmailLog, EmailTemplate
from apps.communication.services import EmailService, NotificationService

User = get_user_model()


class EmailServiceTest(TestCase):
    """Tests pour EmailService."""
    
    def setUp(self):
        """Configuration des tests."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_send_email_creates_log(self):
        """Test que l'envoi d'email crée un log."""
        # Envoyer un email
        log = EmailService.send_email(
            recipient_email='test@example.com',
            subject='Test Email',
            template_name='emails/default.html',
            context={'message': 'Test message'},
            recipient_name='Test User'
        )
        
        # Vérifier que le log a été créé
        self.assertIsInstance(log, EmailLog)
        self.assertEqual(log.recipient_email, 'test@example.com')
        self.assertEqual(log.subject, 'Test Email')
        self.assertEqual(log.recipient_name, 'Test User')
        
        # Vérifier que l'email a été envoyé
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, ['test@example.com'])
        self.assertEqual(sent_email.subject, 'Test Email')
    
    def test_send_email_with_template_uses_configurable_template(self):
        """Test que send_email_with_template utilise les templates configurables."""
        # Créer un template configurable
        template = EmailTemplate.objects.create(
            name='Test Template',
            template_type='custom',
            subject='Template Subject: {{recipient_name}}',
            html_content='<p>Hello {{recipient_name}}!</p>',
            is_default=True,
            is_active=True
        )
        
        # Envoyer un email avec le template
        log = EmailService.send_email_with_template(
            recipient_email='test@example.com',
            template_type='custom',
            context={'recipient_name': 'John Doe'},
            recipient_name='John Doe'
        )
        
        # Vérifier que le log a été créé avec le bon template_type
        self.assertEqual(log.template_type, 'custom')
        self.assertEqual(log.subject, 'Template Subject: John Doe')
        
        # Vérifier que l'email a été envoyé
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, 'Template Subject: John Doe')
    
    def test_send_bulk_emails(self):
        """Test l'envoi d'emails en masse."""
        recipients = [
            'user1@example.com',
            ('user2@example.com', 'User Two'),
            'user3@example.com'
        ]
        
        logs = EmailService.send_bulk_emails(
            recipients=recipients,
            subject='Bulk Email Test',
            template_name='emails/default.html',
            context={'message': 'Bulk message'}
        )
        
        # Vérifier que tous les logs ont été créés
        self.assertEqual(len(logs), 3)
        
        # Vérifier que tous les emails ont été envoyés
        self.assertEqual(len(mail.outbox), 3)
        
        # Vérifier les destinataires
        sent_emails = [email.to[0] for email in mail.outbox]
        self.assertIn('user1@example.com', sent_emails)
        self.assertIn('user2@example.com', sent_emails)
        self.assertIn('user3@example.com', sent_emails)


class NotificationServiceTest(TestCase):
    """Tests pour NotificationService."""
    
    def setUp(self):
        """Configuration des tests."""
        # Créer un mock d'événement
        self.mock_event = MagicMock()
        self.mock_event.title = 'Test Event'
        self.mock_event.description = 'Test Description'
        self.mock_event.start_date = '2024-01-15'
        self.mock_event.start_time = '14:00'
        self.mock_event.location = 'Test Location'
    
    @patch.object(NotificationService, '_get_event_recipients')
    def test_send_event_notification(self, mock_get_recipients):
        """Test l'envoi de notification d'événement."""
        # Configurer le mock
        mock_get_recipients.return_value = [
            {'email': 'user1@example.com', 'name': 'User One'},
            {'email': 'user2@example.com', 'name': 'User Two'}
        ]
        
        # Créer un template par défaut
        EmailTemplate.objects.create(
            name='Event Notification Default',
            template_type='event_notification',
            subject='Event: {{event.title}}',
            html_content='<p>Event: {{event.title}}</p>',
            is_default=True,
            is_active=True
        )
        
        # Envoyer la notification
        logs = NotificationService.send_event_notification(
            event=self.mock_event,
            notification_type='upcoming'
        )
        
        # Vérifier que les logs ont été créés
        self.assertEqual(len(logs), 2)
        
        # Vérifier que les emails ont été envoyés
        self.assertEqual(len(mail.outbox), 2)
    
    @patch.object(NotificationService, '_get_event_recipients')
    def test_send_reminder(self, mock_get_recipients):
        """Test l'envoi de rappel d'événement."""
        # Configurer le mock
        mock_get_recipients.return_value = [
            {'email': 'user1@example.com', 'name': 'User One'}
        ]
        
        # Créer un template par défaut
        EmailTemplate.objects.create(
            name='Event Reminder Default',
            template_type='event_reminder',
            subject='Reminder: {{event.title}}',
            html_content='<p>Reminder: {{event.title}}</p>',
            is_default=True,
            is_active=True
        )
        
        # Envoyer le rappel
        logs = NotificationService.send_reminder(
            event=self.mock_event,
            days_before=1
        )
        
        # Vérifier que le log a été créé
        self.assertEqual(len(logs), 1)
        
        # Vérifier que l'email a été envoyé
        self.assertEqual(len(mail.outbox), 1)


class EmailLogTest(TestCase):
    """Tests pour le modèle EmailLog."""
    
    def test_email_log_properties(self):
        """Test les propriétés du modèle EmailLog."""
        # Créer un log d'email
        log = EmailLog.objects.create(
            recipient_email='test@example.com',
            subject='Test Subject',
            body='Test body',
            status=EmailLog.Status.SENT
        )
        
        # Tester les propriétés
        self.assertTrue(log.is_successful)
        self.assertFalse(log.is_failed)
        self.assertFalse(log.is_pending)
    
    def test_get_stats(self):
        """Test la méthode get_stats."""
        # Créer quelques logs
        EmailLog.objects.create(
            recipient_email='test1@example.com',
            subject='Test 1',
            body='Body 1',
            status=EmailLog.Status.SENT
        )
        EmailLog.objects.create(
            recipient_email='test2@example.com',
            subject='Test 2',
            body='Body 2',
            status=EmailLog.Status.FAILED
        )
        
        # Obtenir les statistiques
        stats = EmailLog.get_stats(days=30)
        
        # Vérifier les statistiques
        self.assertEqual(stats['total'], 2)
        self.assertEqual(stats['sent'], 1)
        self.assertEqual(stats['failed'], 1)
        self.assertEqual(stats['success_rate'], 50.0)
        self.assertEqual(stats['failure_rate'], 50.0)
    
    def test_retry_send(self):
        """Test la méthode retry_send."""
        # Créer un log d'email échoué
        log = EmailLog.objects.create(
            recipient_email='test@example.com',
            subject='Test Subject',
            body='Test body',
            status=EmailLog.Status.FAILED,
            error_message='Test error'
        )
        
        # Tenter de renvoyer
        result = log.retry_send()
        
        # Vérifier que le statut a changé
        self.assertTrue(result)
        log.refresh_from_db()
        self.assertEqual(log.status, EmailLog.Status.PENDING)
        self.assertEqual(log.error_message, '')


class EmailTemplateTest(TestCase):
    """Tests pour le modèle EmailTemplate."""
    
    def test_get_default_template(self):
        """Test la récupération du template par défaut."""
        # Créer un template par défaut
        template = EmailTemplate.objects.create(
            name='Default Template',
            template_type='event_notification',
            subject='Default Subject',
            html_content='<p>Default content</p>',
            is_default=True,
            is_active=True
        )
        
        # Récupérer le template par défaut
        default_template = EmailTemplate.get_default_template('event_notification')
        
        # Vérifier que c'est le bon template
        self.assertEqual(default_template, template)
    
    def test_unique_default_per_type(self):
        """Test qu'il ne peut y avoir qu'un seul template par défaut par type."""
        # Créer le premier template par défaut
        template1 = EmailTemplate.objects.create(
            name='Template 1',
            template_type='event_notification',
            subject='Subject 1',
            html_content='<p>Content 1</p>',
            is_default=True,
            is_active=True
        )
        
        # Créer un second template par défaut du même type
        template2 = EmailTemplate.objects.create(
            name='Template 2',
            template_type='event_notification',
            subject='Subject 2',
            html_content='<p>Content 2</p>',
            is_default=True,
            is_active=True
        )
        
        # Vérifier que seul le second est par défaut
        template1.refresh_from_db()
        self.assertFalse(template1.is_default)
        self.assertTrue(template2.is_default)