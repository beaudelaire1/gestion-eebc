"""
Backend email Hostinger - Intégration SMTP avec validation API Hostinger.
"""
import smtplib
import logging
import requests
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from typing import List, Optional, Dict, Any

from apps.communication.models import EmailLog

logger = logging.getLogger(__name__)


class HostingerAPIValidator:
    """
    Validateur pour l'API Hostinger - vérifie la validité des credentials.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = getattr(settings, 'HOSTINGER_API_BASE_URL', 'https://developers.hostinger.com')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def validate_api_key(self) -> Dict[str, Any]:
        """
        Valide la clé API Hostinger en tentant d'accéder aux domaines.
        
        Returns:
            Dict avec le statut de validation
        """
        try:
            # Test avec l'endpoint des domaines (plus léger)
            response = self.session.get(
                f"{self.base_url}/api/domains/v1/portfolio",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Gérer différents formats de réponse
                if isinstance(data, dict) and 'data' in data:
                    domains = data['data']
                elif isinstance(data, list):
                    domains = data
                else:
                    domains = []
                
                return {
                    'valid': True,
                    'message': 'Clé API Hostinger valide',
                    'domains_count': len(domains)
                }
            elif response.status_code == 401:
                return {
                    'valid': False,
                    'message': 'Clé API Hostinger invalide ou expirée',
                    'error': 'Unauthorized'
                }
            else:
                return {
                    'valid': False,
                    'message': f'Erreur API Hostinger: {response.status_code}',
                    'error': response.text[:200]  # Limiter la taille de l'erreur
                }
                
        except requests.exceptions.Timeout:
            return {
                'valid': False,
                'message': 'Timeout lors de la validation API Hostinger',
                'error': 'Timeout'
            }
        except requests.exceptions.RequestException as e:
            return {
                'valid': False,
                'message': f'Erreur de connexion à l\'API Hostinger: {str(e)[:100]}',
                'error': str(e)[:100]
            }
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Récupère les informations de base du compte.
        
        Returns:
            Dict avec les informations du compte
        """
        try:
            # Essayer d'obtenir la liste des domaines comme proxy pour les infos du compte
            response = self.session.get(
                f"{self.base_url}/api/domains/v1/portfolio",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                # Vérifier si data est un dict avec une clé 'data' ou directement une liste
                if isinstance(data, dict) and 'data' in data:
                    domains = data['data']
                elif isinstance(data, list):
                    domains = data
                else:
                    domains = []
                
                return {
                    'success': True,
                    'domains_count': len(domains),
                    'domains': [domain.get('domain', str(domain)) if isinstance(domain, dict) else str(domain) for domain in domains[:5]],
                    'message': f'Compte actif avec {len(domains)} domaine(s)'
                }
            else:
                return {
                    'success': False,
                    'message': f'Impossible de récupérer les infos du compte: {response.status_code}',
                    'error': response.text[:200]
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Erreur lors de la récupération des infos: {str(e)[:100]}',
                'error': str(e)[:100]
            }


class HostingerEmailBackend(BaseEmailBackend):
    """
    Backend email personnalisé pour Hostinger utilisant SMTP avec validation API.
    
    Configuration requise dans settings:
    - HOSTINGER_API_KEY: Clé API Hostinger (pour validation)
    - HOSTINGER_EMAIL_HOST: Serveur SMTP Hostinger
    - HOSTINGER_EMAIL_PORT: Port SMTP (587 pour TLS, 465 pour SSL)
    - HOSTINGER_EMAIL_USE_TLS: True pour TLS
    - HOSTINGER_EMAIL_USE_SSL: True pour SSL
    - HOSTINGER_EMAIL_HOST_USER: Votre email Hostinger
    - HOSTINGER_EMAIL_HOST_PASSWORD: Mot de passe email
    """
    
    def __init__(self, host=None, port=None, username=None, password=None,
                 use_tls=None, use_ssl=None, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        
        # Configuration Hostinger depuis les settings
        self.api_key = getattr(settings, 'HOSTINGER_API_KEY', '')
        self.host = host or getattr(settings, 'HOSTINGER_EMAIL_HOST', 'smtp.hostinger.com')
        self.port = port or getattr(settings, 'HOSTINGER_EMAIL_PORT', 587)
        self.username = username or getattr(settings, 'HOSTINGER_EMAIL_HOST_USER', '')
        self.password = password or getattr(settings, 'HOSTINGER_EMAIL_HOST_PASSWORD', '')
        self.use_tls = use_tls if use_tls is not None else getattr(settings, 'HOSTINGER_EMAIL_USE_TLS', True)
        self.use_ssl = use_ssl if use_ssl is not None else getattr(settings, 'HOSTINGER_EMAIL_USE_SSL', False)
        self.timeout = getattr(settings, 'HOSTINGER_EMAIL_TIMEOUT', 30)
        
        # Validateur API Hostinger
        self.api_validator = None
        if self.api_key:
            self.api_validator = HostingerAPIValidator(self.api_key)
        
        # Validation de la configuration
        if not self.username or not self.password:
            logger.error("Configuration Hostinger incomplète: username ou password manquant")
        
        if not self.api_key:
            logger.warning("Clé API Hostinger manquante - validation API désactivée")
        
        self.connection = None
        self._api_validated = False
        
        # Initialiser le lock pour la compatibilité avec BaseEmailBackend
        import threading
        self._lock = threading.RLock()
    
    def _validate_api_if_needed(self):
        """
        Valide l'API Hostinger si ce n'est pas déjà fait.
        """
        if not self.api_validator or self._api_validated:
            return
        
        try:
            result = self.api_validator.validate_api_key()
            if result['valid']:
                logger.info("API Hostinger validée avec succès")
                self._api_validated = True
            else:
                logger.warning(f"Validation API Hostinger échouée: {result['message']}")
        except Exception as e:
            logger.warning(f"Erreur lors de la validation API: {e}")
    
    def open(self):
        """
        Ouvre une connexion SMTP avec Hostinger.
        """
        if self.connection:
            return False
        
        # Valider l'API si disponible
        self._validate_api_if_needed()
        
        try:
            if self.use_ssl:
                self.connection = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout)
            else:
                self.connection = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
                if self.use_tls:
                    self.connection.starttls()
            
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            
            logger.info(f"Connexion SMTP Hostinger établie: {self.host}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur connexion SMTP Hostinger: {e}")
            if not self.fail_silently:
                raise
            return False
    
    def close(self):
        """
        Ferme la connexion SMTP.
        """
        if self.connection is None:
            return
        
        try:
            self.connection.quit()
        except Exception as e:
            logger.warning(f"Erreur fermeture connexion SMTP: {e}")
        finally:
            self.connection = None
    
    def send_messages(self, email_messages):
        """
        Envoie une liste de messages email via Hostinger SMTP.
        """
        if not email_messages:
            return 0
        
        with self._lock:
            new_conn_created = self.open()
            if not self.connection:
                return 0
            
            num_sent = 0
            for message in email_messages:
                sent = self._send_message(message)
                if sent:
                    num_sent += 1
            
            if new_conn_created:
                self.close()
        
        return num_sent
    
    def _send_message(self, email_message):
        """
        Envoie un message email individuel et log le résultat.
        """
        if not self.connection:
            return False
        
        # Créer le log avant l'envoi
        log = self._create_email_log(email_message)
        
        try:
            # Préparer le message MIME
            msg = self._prepare_mime_message(email_message)
            
            # Envoyer via SMTP
            from_email = email_message.from_email or self.username
            recipients = email_message.recipients()
            
            self.connection.sendmail(from_email, recipients, msg.as_string())
            
            # Marquer comme envoyé
            log.status = 'sent'
            log.sent_at = timezone.now()
            log.save()
            
            logger.info(f"Email envoyé via Hostinger à {recipients}: {email_message.subject}")
            return True
            
        except Exception as e:
            # Marquer comme échoué
            log.status = 'failed'
            log.error_message = str(e)
            log.save()
            
            logger.error(f"Échec envoi email Hostinger à {email_message.recipients()}: {e}")
            
            if not self.fail_silently:
                raise
            return False
    
    def _prepare_mime_message(self, email_message):
        """
        Prépare le message MIME à partir du message Django.
        """
        if email_message.alternatives:
            # Message avec alternatives (HTML + texte)
            msg = MIMEMultipart('alternative')
            
            # Partie texte
            if email_message.body:
                text_part = MIMEText(email_message.body, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # Parties alternatives (HTML)
            for content, mimetype in email_message.alternatives:
                if mimetype == 'text/html':
                    html_part = MIMEText(content, 'html', 'utf-8')
                    msg.attach(html_part)
        else:
            # Message texte simple
            msg = MIMEText(email_message.body, 'plain', 'utf-8')
        
        # En-têtes
        msg['Subject'] = email_message.subject
        msg['From'] = email_message.from_email or self.username
        msg['To'] = ', '.join(email_message.to)
        
        if email_message.cc:
            msg['Cc'] = ', '.join(email_message.cc)
        
        if email_message.reply_to:
            msg['Reply-To'] = ', '.join(email_message.reply_to)
        
        # Pièces jointes
        if hasattr(email_message, 'attachments') and email_message.attachments:
            if not isinstance(msg, MIMEMultipart):
                # Convertir en multipart pour les pièces jointes
                original_msg = msg
                msg = MIMEMultipart()
                msg.attach(original_msg)
                
                # Copier les en-têtes
                for key, value in original_msg.items():
                    msg[key] = value
            
            for attachment in email_message.attachments:
                self._attach_file(msg, attachment)
        
        return msg
    
    def _attach_file(self, msg, attachment):
        """
        Ajoute une pièce jointe au message MIME.
        """
        if isinstance(attachment, tuple):
            filename, content, mimetype = attachment
            
            part = MIMEBase(*mimetype.split('/', 1))
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            msg.attach(part)
    
    def _create_email_log(self, email_message):
        """
        Crée un log pour l'email avant l'envoi.
        """
        recipients = email_message.recipients()
        recipient_email = recipients[0] if recipients else ''
        
        return EmailLog.objects.create(
            recipient_email=recipient_email,
            recipient_name='',  # Pas disponible dans email_message
            subject=email_message.subject,
            body=email_message.body,
            status='pending'
        )


class HostingerEmailService:
    """
    Service haut niveau pour l'envoi d'emails via Hostinger.
    """
    
    @staticmethod
    def send_email(
        recipient_email: str,
        subject: str,
        html_content: str = None,
        text_content: str = None,
        template_name: str = None,
        context: Dict[str, Any] = None,
        recipient_name: str = '',
        from_email: str = None,
        attachments: List = None,
        fail_silently: bool = False
    ) -> EmailLog:
        """
        Envoie un email via Hostinger avec logging avancé.
        
        Args:
            recipient_email: Email du destinataire
            subject: Sujet de l'email
            html_content: Contenu HTML
            text_content: Contenu texte
            template_name: Template Django à utiliser
            context: Contexte pour le template
            recipient_name: Nom du destinataire
            from_email: Email expéditeur
            attachments: Liste des pièces jointes
            fail_silently: Ne pas lever d'exception en cas d'erreur
            
        Returns:
            EmailLog: Log de l'email
        """
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        
        # Configuration par défaut
        from_email = from_email or getattr(settings, 'HOSTINGER_EMAIL_HOST_USER', settings.DEFAULT_FROM_EMAIL)
        context = context or {}
        attachments = attachments or []
        
        # Générer le contenu depuis template si fourni
        if template_name and not html_content:
            context.update({
                'site_name': getattr(settings, 'SITE_NAME', 'EEBC'),
                'site_url': getattr(settings, 'SITE_URL', 'localhost'),
                'current_year': timezone.now().year,
            })
            html_content = render_to_string(template_name, context)
        
        # Générer le contenu texte si absent
        if html_content and not text_content:
            text_content = strip_tags(html_content)
        
        # Créer le message email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content or '',
            from_email=from_email,
            to=[recipient_email]
        )
        
        # Ajouter le contenu HTML
        if html_content:
            email.attach_alternative(html_content, "text/html")
        
        # Ajouter les pièces jointes
        for attachment in attachments:
            if isinstance(attachment, tuple) and len(attachment) == 3:
                filename, content, mimetype = attachment
                email.attach(filename, content, mimetype)
        
        # Créer le log
        log = EmailLog.objects.create(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            body=text_content or html_content,
            status='pending'
        )
        
        try:
            # Utiliser le backend Hostinger
            backend = HostingerEmailBackend(fail_silently=False)
            backend.send_messages([email])
            
            # Le log sera mis à jour par le backend
            log.refresh_from_db()
            
        except Exception as e:
            log.status = 'failed'
            log.error_message = str(e)
            log.save()
            
            logger.error(f"Erreur service Hostinger email: {e}")
            
            if not fail_silently:
                raise
        
        return log
    
    @staticmethod
    def send_bulk_emails(
        recipients: List[tuple],
        subject: str,
        html_content: str = None,
        text_content: str = None,
        template_name: str = None,
        context: Dict[str, Any] = None,
        from_email: str = None,
        fail_silently: bool = True
    ) -> List[EmailLog]:
        """
        Envoie des emails en masse via Hostinger.
        
        Args:
            recipients: Liste de tuples (email, name)
            subject: Sujet commun
            html_content: Contenu HTML
            text_content: Contenu texte
            template_name: Template à utiliser
            context: Contexte pour le template
            from_email: Email expéditeur
            fail_silently: Ne pas lever d'exception
            
        Returns:
            List[EmailLog]: Liste des logs créés
        """
        logs = []
        
        for recipient in recipients:
            if isinstance(recipient, tuple):
                email, name = recipient
            else:
                email, name = recipient, ''
            
            log = HostingerEmailService.send_email(
                recipient_email=email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                template_name=template_name,
                context=context,
                recipient_name=name,
                from_email=from_email,
                fail_silently=fail_silently
            )
            logs.append(log)
        
        return logs
    
    @staticmethod
    def test_connection() -> Dict[str, Any]:
        """
        Teste la connexion SMTP et API Hostinger.
        
        Returns:
            Dict avec le statut du test
        """
        try:
            backend = HostingerEmailBackend()
            
            # Test de l'API si disponible
            api_result = None
            if backend.api_validator:
                api_result = backend.api_validator.validate_api_key()
            
            # Test de la connexion SMTP
            smtp_success = backend.open()
            if smtp_success:
                backend.close()
            
            return {
                'success': smtp_success,
                'message': 'Connexion Hostinger réussie' if smtp_success else 'Échec connexion SMTP Hostinger',
                'smtp_config': {
                    'host': backend.host,
                    'port': backend.port,
                    'username': backend.username,
                    'use_tls': backend.use_tls,
                    'use_ssl': backend.use_ssl
                },
                'api_validation': api_result,
                'api_available': backend.api_validator is not None
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Erreur test connexion: {str(e)}',
                'error': str(e),
                'smtp_config': {},
                'api_validation': None,
                'api_available': False
            }
    
    @staticmethod
    def get_account_info() -> Dict[str, Any]:
        """
        Récupère les informations du compte Hostinger via l'API.
        
        Returns:
            Dict avec les informations du compte
        """
        api_key = getattr(settings, 'HOSTINGER_API_KEY', '')
        if not api_key:
            return {
                'success': False,
                'message': 'Clé API Hostinger non configurée'
            }
        
        try:
            validator = HostingerAPIValidator(api_key)
            return validator.get_account_info()
        except Exception as e:
            return {
                'success': False,
                'message': f'Erreur récupération infos compte: {str(e)}',
                'error': str(e)
            }