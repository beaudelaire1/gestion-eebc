"""
Commande Django pour tester la configuration email Hostinger.
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from apps.core.infrastructure.hostinger_email_backend import HostingerEmailService


class Command(BaseCommand):
    help = 'Teste la configuration email Hostinger'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--send-test',
            type=str,
            help='Envoie un email de test à l\'adresse spécifiée'
        )
        parser.add_argument(
            '--connection-only',
            action='store_true',
            help='Teste uniquement la connexion SMTP sans envoyer d\'email'
        )
        parser.add_argument(
            '--account-info',
            action='store_true',
            help='Affiche les informations du compte Hostinger via l\'API'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.HTTP_INFO('=== Test Configuration Hostinger Email ===')
        )
        
        # Vérifier la configuration
        self._check_configuration()
        
        if options['connection_only']:
            # Test de connexion uniquement
            self._test_connection()
        elif options['account_info']:
            # Informations du compte
            self._show_account_info()
        elif options['send_test']:
            # Test avec envoi d'email
            self._test_send_email(options['send_test'])
        else:
            # Test complet
            self._test_connection()
            self._prompt_test_email()
    
    def _check_configuration(self):
        """Vérifie la configuration Hostinger."""
        self.stdout.write('\n1. Vérification de la configuration...')
        
        required_settings = [
            'HOSTINGER_EMAIL_HOST',
            'HOSTINGER_EMAIL_HOST_USER',
            'HOSTINGER_EMAIL_HOST_PASSWORD'
        ]
        
        missing_settings = []
        for setting in required_settings:
            if not getattr(settings, setting, None):
                missing_settings.append(setting)
        
        if missing_settings:
            self.stdout.write(
                self.style.ERROR(
                    f'Configuration incomplète. Variables manquantes: {", ".join(missing_settings)}'
                )
            )
            raise CommandError('Configuration Hostinger incomplète')
        
        # Afficher la configuration actuelle
        self.stdout.write(f'   Host: {settings.HOSTINGER_EMAIL_HOST}')
        self.stdout.write(f'   Port: {settings.HOSTINGER_EMAIL_PORT}')
        self.stdout.write(f'   User: {settings.HOSTINGER_EMAIL_HOST_USER}')
        self.stdout.write(f'   TLS: {settings.HOSTINGER_EMAIL_USE_TLS}')
        self.stdout.write(f'   SSL: {settings.HOSTINGER_EMAIL_USE_SSL}')
        
        # Vérifier la clé API
        api_key = getattr(settings, 'HOSTINGER_API_KEY', '')
        if api_key:
            self.stdout.write(f'   API Key: {"*" * 20}...{api_key[-4:] if len(api_key) > 4 else "****"}')
        else:
            self.stdout.write(self.style.WARNING('   API Key: Non configurée'))
        
        self.stdout.write(self.style.SUCCESS('   ✓ Configuration OK'))
    
    def _test_connection(self):
        """Teste la connexion SMTP et API."""
        self.stdout.write('\n2. Test de connexion SMTP et API...')
        
        try:
            result = HostingerEmailService.test_connection()
            
            if result.get('success', False):
                self.stdout.write(self.style.SUCCESS('   ✓ Connexion SMTP réussie'))
                smtp_config = result.get('smtp_config', {})
                self.stdout.write(f'   Serveur: {smtp_config.get("host", "N/A")}:{smtp_config.get("port", "N/A")}')
                self.stdout.write(f'   Utilisateur: {smtp_config.get("username", "N/A")}')
                
                # Test API si disponible
                api_validation = result.get('api_validation')
                if api_validation:
                    if api_validation.get('valid'):
                        self.stdout.write(self.style.SUCCESS('   ✓ API Hostinger validée'))
                        if 'domains_count' in api_validation:
                            self.stdout.write(f'   Domaines: {api_validation["domains_count"]}')
                    else:
                        self.stdout.write(self.style.WARNING(f'   ⚠ API Hostinger: {api_validation.get("message", "Erreur inconnue")}'))
                else:
                    self.stdout.write(self.style.WARNING('   ⚠ API Hostinger non configurée'))
            else:
                self.stdout.write(self.style.ERROR('   ✗ Échec de connexion'))
                self.stdout.write(f'   Erreur: {result.get("message", "Erreur inconnue")}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ Erreur: {str(e)}'))
    
    def _show_account_info(self):
        """Affiche les informations du compte Hostinger."""
        self.stdout.write('\n3. Informations du compte Hostinger...')
        
        try:
            result = HostingerEmailService.get_account_info()
            
            if result['success']:
                self.stdout.write(self.style.SUCCESS('   ✓ Informations récupérées'))
                self.stdout.write(f'   Message: {result["message"]}')
                
                if 'domains_count' in result:
                    self.stdout.write(f'   Nombre de domaines: {result["domains_count"]}')
                
                if 'domains' in result and result['domains']:
                    self.stdout.write('   Domaines (premiers 5):')
                    for domain in result['domains']:
                        self.stdout.write(f'     - {domain}')
            else:
                self.stdout.write(self.style.ERROR('   ✗ Échec récupération'))
                self.stdout.write(f'   Erreur: {result["message"]}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ Erreur: {str(e)}'))
    
    def _test_send_email(self, recipient_email):
        """Teste l'envoi d'un email."""
        self.stdout.write(f'\n3. Test d\'envoi d\'email à {recipient_email}...')
        
        try:
            log = HostingerEmailService.send_email(
                recipient_email=recipient_email,
                subject='Test Email Hostinger - EEBC',
                html_content=self._get_test_email_content(),
                text_content='Ceci est un email de test depuis l\'intégration Hostinger de EEBC.',
                fail_silently=False
            )
            
            if log.status == 'sent':
                self.stdout.write(self.style.SUCCESS('   ✓ Email envoyé avec succès'))
                self.stdout.write(f'   ID du log: {log.id}')
                self.stdout.write(f'   Envoyé à: {log.sent_at}')
            else:
                self.stdout.write(self.style.ERROR('   ✗ Échec d\'envoi'))
                self.stdout.write(f'   Erreur: {log.error_message}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ Erreur: {str(e)}'))
    
    def _prompt_test_email(self):
        """Demande à l'utilisateur s'il veut tester l'envoi d'email."""
        response = input('\nVoulez-vous tester l\'envoi d\'un email ? (o/N): ')
        
        if response.lower() in ['o', 'oui', 'y', 'yes']:
            email = input('Adresse email de test: ')
            if email:
                self._test_send_email(email)
            else:
                self.stdout.write(self.style.WARNING('Aucune adresse fournie, test d\'envoi ignoré'))
    
    def _get_test_email_content(self):
        """Génère le contenu HTML de l'email de test."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Test Email Hostinger</title>
        </head>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
            <h2 style="color: #2c3e50;">Test Email Hostinger - EEBC</h2>
            
            <p>Bonjour,</p>
            
            <p>Ceci est un email de test pour vérifier l'intégration Hostinger Email dans le système de gestion EEBC.</p>
            
            <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #28a745; margin: 20px 0;">
                <strong>✓ Configuration Hostinger fonctionnelle</strong><br>
                L'envoi d'emails via Hostinger est opérationnel.
            </div>
            
            <p>Fonctionnalités testées :</p>
            <ul>
                <li>Connexion SMTP Hostinger</li>
                <li>Authentification email</li>
                <li>Envoi HTML et texte</li>
                <li>Logging des emails</li>
            </ul>
            
            <hr style="margin: 30px 0;">
            
            <p style="color: #6c757d; font-size: 12px;">
                Email généré automatiquement par le système EEBC<br>
                Intégration Hostinger Email - Test de configuration
            </p>
        </body>
        </html>
        """