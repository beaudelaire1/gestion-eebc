# Communication App - Système de Notifications Email

## Vue d'ensemble

Le module `communication` fournit un système complet de notifications email pour l'application EEBC, avec des templates configurables, un logging automatique et des services centralisés.

## Fonctionnalités

### 1. Service d'Email Centralisé (`EmailService`)

- Envoi d'emails avec templates HTML
- Templates configurables depuis l'admin Django
- Logging automatique de tous les envois
- Gestion des erreurs et retry
- Support des emails en masse

### 2. Service de Notifications (`NotificationService`)

- Notifications d'événements
- Rappels automatiques
- Confirmations de transport
- Gestion des destinataires

### 3. Templates Configurables (`EmailTemplate`)

- Templates éditables via l'admin Django
- Variables dynamiques avec syntaxe Django
- Types prédéfinis (événements, transport, etc.)
- Templates par défaut avec fallback

### 4. Logging Complet (`EmailLog`)

- Statut de chaque email (envoyé, échoué, en attente)
- Métadonnées complètes
- Statistiques et rapports
- Gestion des erreurs

## Utilisation

### Envoi d'Email Simple

```python
from apps.communication.services import EmailService

# Envoi avec template configurable
log = EmailService.send_email_with_template(
    recipient_email='user@example.com',
    template_type='event_notification',
    context={
        'event': event_instance,
        'recipient_name': 'John Doe'
    },
    recipient_name='John Doe'
)
```

### Notification d'Événement

```python
from apps.communication.services import NotificationService

# Notification d'événement
logs = NotificationService.send_event_notification(
    event=event_instance,
    notification_type='upcoming'  # ou 'reminder', 'cancelled'
)

# Rappel d'événement
logs = NotificationService.send_reminder(
    event=event_instance,
    days_before=1
)
```

### Emails en Masse

```python
recipients = [
    'user1@example.com',
    ('user2@example.com', 'User Two'),
    'user3@example.com'
]

logs = EmailService.send_bulk_emails(
    recipients=recipients,
    subject='Notification importante',
    template_name='emails/notification.html',
    context={'message': 'Votre message'}
)
```

## Configuration des Templates

### Via l'Admin Django

1. Aller dans **Communication > Templates d'emails**
2. Créer un nouveau template ou modifier un existant
3. Définir le type, sujet et contenu HTML
4. Utiliser les variables Django : `{{variable_name}}`

### Variables Disponibles

#### Templates d'Événements
- `{{event.title}}` : Titre de l'événement
- `{{event.description}}` : Description
- `{{event.start_date}}` : Date de début
- `{{event.start_time}}` : Heure de début
- `{{event.location}}` : Lieu
- `{{recipient_name}}` : Nom du destinataire

#### Templates de Transport
- `{{transport_request.destination}}` : Destination
- `{{transport_request.pickup_location}}` : Lieu de prise en charge
- `{{driver.name}}` : Nom du chauffeur
- `{{has_driver}}` : True si chauffeur assigné

#### Variables Globales
- `{{site_name}}` : Nom du site
- `{{site_url}}` : URL du site
- `{{current_year}}` : Année actuelle
- `{{contact_email}}` : Email de contact

## Commandes de Gestion

### Créer les Templates par Défaut

```bash
python manage.py create_default_email_templates
```

### Statistiques d'Emails

```bash
# Statistiques des 30 derniers jours
python manage.py email_stats

# Statistiques avec détail des erreurs
python manage.py email_stats --show-errors

# Statistiques sur une période spécifique
python manage.py email_stats --days 7
```

### Nettoyage des Logs

```bash
# Nettoyer les logs de plus d'un an
python manage.py cleanup_email_logs --days 365

# Mode dry-run (simulation)
python manage.py cleanup_email_logs --dry-run

# Conserver les emails échoués
python manage.py cleanup_email_logs --keep-failed
```

## Monitoring et Statistiques

### Via l'Admin Django

- **Logs d'emails** : Voir tous les emails envoyés avec statut
- **Statistiques** : Taux de succès, erreurs fréquentes
- **Actions** : Marquer comme échoué, exporter les erreurs

### Via les Modèles

```python
from apps.communication.models import EmailLog

# Statistiques des 30 derniers jours
stats = EmailLog.get_stats(days=30)
print(f"Taux de succès: {stats['success_rate']}%")

# Erreurs fréquentes
errors = EmailLog.get_failed_emails_by_error(days=7)
for error, count in errors.items():
    print(f"{count}x: {error}")
```

## Configuration SMTP

Assurez-vous que les paramètres SMTP sont configurés dans `settings.py` :

```python
# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'EEBC <noreply@eebc-guyane.org>'
```

## Tests

Exécuter les tests :

```bash
python manage.py test apps.communication.tests
```

## Sécurité

- Tous les emails sont loggés avec métadonnées
- Validation des templates avant envoi
- Gestion des erreurs sans exposition d'informations sensibles
- Rate limiting recommandé au niveau serveur

## Maintenance

### Tâches Recommandées

1. **Nettoyage mensuel** : Supprimer les anciens logs
2. **Monitoring** : Surveiller le taux d'échec
3. **Templates** : Réviser et optimiser les templates
4. **Performance** : Analyser les temps d'envoi

### Alertes à Configurer

- Taux d'échec > 10%
- Emails en attente > 100
- Erreurs SMTP récurrentes