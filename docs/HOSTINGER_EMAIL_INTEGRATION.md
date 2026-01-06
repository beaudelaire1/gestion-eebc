# Intégration Email Hostinger - EEBC

## Vue d'ensemble

Cette intégration permet d'utiliser les services email Hostinger avec le système de gestion EEBC. Elle combine l'API Hostinger pour la validation et SMTP pour l'envoi d'emails.

## Configuration requise

### 1. Credentials Hostinger

Vous devez avoir :
- **Clé API Hostinger** : Obtenue depuis votre compte Hostinger
- **Adresse email** : Votre email hébergé chez Hostinger
- **Mot de passe email** : Le mot de passe de votre compte email

### 2. Variables d'environnement

Ajoutez ces variables à votre fichier `.env` :

```bash
# Backend email - utiliser 'hostinger' pour activer l'intégration
EMAIL_BACKEND=hostinger

# Configuration Hostinger Email
HOSTINGER_API_KEY=votre-cle-api-hostinger
HOSTINGER_EMAIL_HOST=smtp.hostinger.com
HOSTINGER_EMAIL_PORT=587
HOSTINGER_EMAIL_USE_TLS=True
HOSTINGER_EMAIL_USE_SSL=False
HOSTINGER_EMAIL_HOST_USER=votre-email@votre-domaine.com
HOSTINGER_EMAIL_HOST_PASSWORD=votre-mot-de-passe-email

# Configuration avancée (optionnel)
HOSTINGER_EMAIL_TIMEOUT=30
HOSTINGER_EMAIL_MAX_RETRIES=3
HOSTINGER_API_BASE_URL=https://developers.hostinger.com

# Expéditeur par défaut
DEFAULT_FROM_EMAIL=EEBC <noreply@votre-domaine.com>
```

## Fonctionnalités

### 1. Validation API

L'intégration valide automatiquement votre clé API Hostinger au premier envoi d'email pour s'assurer que :
- La clé API est valide
- Le compte est actif
- Les domaines sont accessibles

### 2. Envoi SMTP sécurisé

- Connexion TLS/SSL sécurisée
- Authentification par username/password
- Gestion des timeouts et retry
- Logging complet des emails

### 3. Logging avancé

Tous les emails sont loggés dans la base de données avec :
- Statut d'envoi (pending, sent, failed)
- Timestamp d'envoi
- Messages d'erreur détaillés
- Informations du destinataire

## Utilisation

### 1. Envoi d'email simple

```python
from apps.core.infrastructure.hostinger_email_backend import HostingerEmailService

# Envoi d'un email
log = HostingerEmailService.send_email(
    recipient_email='destinataire@example.com',
    subject='Test Email',
    html_content='<h1>Bonjour</h1><p>Ceci est un test.</p>',
    text_content='Bonjour\n\nCeci est un test.'
)

print(f"Email envoyé: {log.status}")
```

### 2. Envoi avec template Django

```python
log = HostingerEmailService.send_email(
    recipient_email='destinataire@example.com',
    subject='Notification EEBC',
    template_name='emails/notification.html',
    context={
        'user_name': 'Jean Dupont',
        'message': 'Votre inscription a été confirmée.'
    }
)
```

### 3. Envoi en masse

```python
recipients = [
    ('jean@example.com', 'Jean Dupont'),
    ('marie@example.com', 'Marie Martin'),
]

logs = HostingerEmailService.send_bulk_emails(
    recipients=recipients,
    subject='Newsletter EEBC',
    template_name='emails/newsletter.html',
    context={'month': 'Janvier 2026'}
)
```

## Commandes de gestion

### 1. Test de configuration

```bash
# Test complet (connexion + envoi optionnel)
python manage.py test_hostinger_email

# Test de connexion uniquement
python manage.py test_hostinger_email --connection-only

# Informations du compte
python manage.py test_hostinger_email --account-info

# Envoi d'un email de test
python manage.py test_hostinger_email --send-test destinataire@example.com
```

### 2. Exemples de sortie

```
=== Test Configuration Hostinger Email ===

1. Vérification de la configuration...
   Host: smtp.hostinger.com
   Port: 587
   User: noreply@eebc-guyane.org
   TLS: True
   SSL: False
   API Key: ********************abc123
   ✓ Configuration OK

2. Test de connexion SMTP et API...
   ✓ Connexion SMTP réussie
   Serveur: smtp.hostinger.com:587
   Utilisateur: noreply@eebc-guyane.org
   ✓ API Hostinger validée
   Domaines: 3
```

## Dépannage

### 1. Erreurs communes

#### Erreur d'authentification SMTP
```
Erreur connexion SMTP Hostinger: (535, 'Authentication failed')
```
**Solution** : Vérifiez votre email et mot de passe dans les variables d'environnement.

#### API Key invalide
```
API Hostinger: Clé API Hostinger invalide ou expirée
```
**Solution** : Régénérez votre clé API depuis votre compte Hostinger.

#### Timeout de connexion
```
Timeout lors de la validation API Hostinger
```
**Solution** : Vérifiez votre connexion internet et les paramètres de firewall.

### 2. Logs de débogage

Activez les logs détaillés dans `settings/dev.py` :

```python
LOGGING['loggers']['apps.core.infrastructure'] = {
    'handlers': ['console', 'file_django'],
    'level': 'DEBUG',
    'propagate': True,
}
```

### 3. Test manuel

```python
# Dans le shell Django
from apps.core.infrastructure.hostinger_email_backend import HostingerEmailService

# Test de connexion
result = HostingerEmailService.test_connection()
print(result)

# Informations du compte
info = HostingerEmailService.get_account_info()
print(info)
```

## Sécurité

### 1. Protection des credentials

- Ne jamais commiter les clés API dans le code
- Utiliser des variables d'environnement
- Rotation régulière des mots de passe
- Surveillance des logs d'accès

### 2. Chiffrement

- Toutes les connexions utilisent TLS/SSL
- Les mots de passe ne sont jamais loggés
- Les clés API sont masquées dans les logs

## Performance

### 1. Optimisations

- Connexions SMTP réutilisées
- Validation API mise en cache
- Timeouts configurables
- Retry automatique

### 2. Monitoring

- Logs détaillés de tous les envois
- Métriques de performance
- Alertes en cas d'échec

## Support

Pour toute question ou problème :

1. Consultez les logs Django : `logs/django.log`
2. Vérifiez les logs d'erreur : `logs/error.log`
3. Utilisez la commande de test : `python manage.py test_hostinger_email`
4. Consultez la documentation Hostinger : https://developers.hostinger.com

## Changelog

### Version 1.0.0 (Janvier 2026)
- Intégration initiale Hostinger
- Support SMTP avec validation API
- Commandes de gestion et test
- Documentation complète