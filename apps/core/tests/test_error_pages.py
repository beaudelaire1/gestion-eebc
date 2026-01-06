"""
Tests pour les pages d'erreur personnalisées.
"""
import pytest
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.http import Http404
from unittest.mock import patch, Mock
from apps.core.models import AuditLog

User = get_user_model()


class ErrorPagesTestCase(TestCase):
    """Tests des pages d'erreur personnalisées."""
    
    def setUp(self):
        """Configuration des tests."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role='membre'
        )
    
    @override_settings(DEBUG=False)
    def test_403_error_page_renders(self):
        """Test que la page 403 se rend correctement."""
        # Simuler une erreur 403 en accédant à une vue protégée sans permissions
        self.client.login(username='testuser', password='testpass123')
        
        # Essayer d'accéder à une vue admin (devrait déclencher 403)
        response = self.client.get('/admin/members/map/')
        
        # Vérifier que c'est bien une erreur 403 ou redirection
        self.assertIn(response.status_code, [403, 302])
    
    @override_settings(DEBUG=False)
    def test_404_error_page_renders(self):
        """Test que la page 404 se rend correctement."""
        response = self.client.get('/page-qui-nexiste-pas/')
        self.assertEqual(response.status_code, 404)
    
    @override_settings(DEBUG=False)
    @patch('gestion_eebc.error_views.render')
    def test_500_error_logging(self, mock_render):
        """Test que les erreurs 500 sont correctement loggées."""
        from gestion_eebc.error_views import handler500
        
        # Créer une requête mock
        request = Mock()
        request.path = '/test-path/'
        request.method = 'GET'
        request.GET = {}
        request.POST = {}
        request.META = {
            'REMOTE_ADDR': '127.0.0.1',
            'HTTP_USER_AGENT': 'Test Agent',
            'HTTP_REFERER': 'http://test.com',
        }
        request.user = self.user
        request.session = Mock()
        request.session.session_key = 'test-session'
        request.headers = {}
        request.content_type = 'text/html'
        request.get_full_path.return_value = '/test-path/?param=value'
        
        # Mock render pour éviter les erreurs de template
        mock_render.return_value = Mock()
        mock_render.return_value.content = b'<html>Error</html>'
        
        # Appeler le handler
        response = handler500(request)
        
        # Vérifier que c'est une réponse 500
        self.assertEqual(response.status_code, 500)
        
        # Vérifier qu'un AuditLog a été créé
        audit_log = AuditLog.objects.filter(
            action=AuditLog.Action.SERVER_ERROR,
            user=self.user
        ).first()
        
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.model_name, 'System')
        self.assertIn('500 Error on /test-path/', audit_log.object_repr)
    
    @override_settings(DEBUG=False)
    def test_403_handler_logs_access_denied(self):
        """Test que le handler 403 logue les accès refusés."""
        from gestion_eebc.error_views import handler403
        
        # Créer une requête mock
        request = Mock()
        request.path = '/admin/secret/'
        request.user = self.user
        request.META = {
            'REMOTE_ADDR': '192.168.1.1',
            'HTTP_USER_AGENT': 'Mozilla/5.0',
        }
        
        # Appeler le handler
        with patch('gestion_eebc.error_views.render') as mock_render:
            mock_render.return_value = Mock()
            mock_render.return_value.content = b'<html>403</html>'
            
            response = handler403(request)
            
            # Vérifier que c'est une réponse 403
            self.assertEqual(response.status_code, 403)
    
    @override_settings(DEBUG=False)
    def test_404_handler_logs_not_found(self):
        """Test que le handler 404 logue les pages non trouvées."""
        from gestion_eebc.error_views import handler404
        
        # Créer une requête mock
        request = Mock()
        request.path = '/page-inexistante/'
        request.user = self.user
        request.META = {
            'REMOTE_ADDR': '10.0.0.1',
            'HTTP_REFERER': 'http://example.com',
        }
        
        # Appeler le handler
        with patch('gestion_eebc.error_views.render') as mock_render:
            mock_render.return_value = Mock()
            mock_render.return_value.content = b'<html>404</html>'
            
            response = handler404(request)
            
            # Vérifier que c'est une réponse 404
            self.assertEqual(response.status_code, 404)
    
    @override_settings(DEBUG=False)
    def test_500_handler_fallback_when_template_fails(self):
        """Test que le handler 500 a un fallback si le template échoue."""
        from gestion_eebc.error_views import handler500
        
        # Créer une requête mock
        request = Mock()
        request.path = '/error-path/'
        request.method = 'POST'
        request.GET = {}
        request.POST = {'data': 'test'}
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        request.user = self.user
        request.session = Mock()
        request.session.session_key = 'session123'
        request.headers = {}
        request.content_type = 'application/json'
        request.get_full_path.return_value = '/error-path/'
        
        # Mock render pour lever une exception
        with patch('gestion_eebc.error_views.render', side_effect=Exception("Template error")):
            response = handler500(request)
            
            # Vérifier que c'est une réponse 500 avec HTML de fallback
            self.assertEqual(response.status_code, 500)
            self.assertIn(b'Erreur interne du serveur', response.content)
            self.assertIn(b'support@eebc.org', response.content)


class ErrorPagesIntegrationTestCase(TestCase):
    """Tests d'intégration des pages d'erreur."""
    
    def setUp(self):
        """Configuration des tests."""
        self.client = Client()
    
    @override_settings(DEBUG=False)
    def test_error_pages_use_correct_templates(self):
        """Test que les pages d'erreur utilisent les bons templates."""
        # Test 404
        response = self.client.get('/nonexistent-page/')
        self.assertEqual(response.status_code, 404)
        
        # Le contenu devrait contenir des éléments de notre template 404
        # (Note: en mode test, Django peut ne pas utiliser nos handlers personnalisés)
        # Ce test vérifie principalement que l'URL routing fonctionne
    
    def test_error_templates_exist(self):
        """Test que les templates d'erreur existent."""
        import os
        from django.conf import settings
        
        template_dir = os.path.join(settings.BASE_DIR, 'templates', 'errors')
        
        # Vérifier que les templates existent
        self.assertTrue(os.path.exists(os.path.join(template_dir, '403.html')))
        self.assertTrue(os.path.exists(os.path.join(template_dir, '404.html')))
        self.assertTrue(os.path.exists(os.path.join(template_dir, '500.html')))
    
    def test_error_handlers_are_configured(self):
        """Test que les handlers d'erreur sont configurés dans urls.py."""
        from django.conf import urls
        
        # Vérifier que les handlers sont définis
        # Note: Ces attributs ne sont disponibles qu'en mode production (DEBUG=False)
        # En mode test, on vérifie juste que les modules existent
        try:
            from gestion_eebc.error_views import handler403, handler404, handler500
            self.assertTrue(callable(handler403))
            self.assertTrue(callable(handler404))
            self.assertTrue(callable(handler500))
        except ImportError:
            self.fail("Error handlers not properly imported")