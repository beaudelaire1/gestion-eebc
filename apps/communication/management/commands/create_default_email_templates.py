"""
Commande de gestion pour créer les templates d'emails par défaut.
"""
from django.core.management.base import BaseCommand
from apps.communication.models import EmailTemplate


class Command(BaseCommand):
    help = 'Crée les templates d\'emails par défaut dans la base de données'

    def handle(self, *args, **options):
        """Crée les templates d'emails par défaut."""
        
        templates_data = [
            {
                'name': 'Notification d\'événement par défaut',
                'template_type': 'event_notification',
                'subject': '📅 Nouvel événement : {{event.title}}',
                'html_content': '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nouvel événement : {{event.title}}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #2c3e50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }
        .content { background-color: #f8f9fa; padding: 30px; border-radius: 0 0 5px 5px; }
        .event-details { background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #3498db; }
        .footer { text-align: center; margin-top: 30px; padding: 20px; background-color: #ecf0f1; border-radius: 5px; font-size: 12px; color: #7f8c8d; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{site_name}}</h1>
        <h2>📅 Nouvel Événement</h2>
    </div>
    
    <div class="content">
        {% if recipient_name %}
            <p>Cher(e) {{recipient_name}},</p>
        {% else %}
            <p>Bonjour,</p>
        {% endif %}
        
        <p>Nous avons le plaisir de vous annoncer un nouvel événement :</p>
        
        <div class="event-details">
            <h3>{{event.title}}</h3>
            {% if event.description %}
                <p>{{event.description}}</p>
            {% endif %}
            
            <p><strong>📅 Date :</strong> {{event.start_date|date:"d/m/Y"}}</p>
            {% if event.start_time %}
                <p><strong>🕐 Heure :</strong> {{event.start_time|time:"H:i"}}</p>
            {% endif %}
            {% if event.location %}
                <p><strong>📍 Lieu :</strong> {{event.location}}</p>
            {% endif %}
        </div>
        
        <p>Nous espérons vous y voir nombreux !</p>
        
        <p>Que Dieu vous bénisse,</p>
        <p><strong>L'équipe EEBC</strong></p>
    </div>
    
    <div class="footer">
        <p>{{site_name}}<br>
        {% if contact_email %}Email: {{contact_email}}{% endif %}</p>
        <p>© {{current_year}} EEBC. Tous droits réservés.</p>
    </div>
</body>
</html>
                ''',
                'is_default': True,
                'variables_help': '''
Variables disponibles :
- event.title : Titre de l'événement
- event.description : Description de l'événement
- event.start_date : Date de début
- event.start_time : Heure de début
- event.location : Lieu de l'événement
- recipient_name : Nom du destinataire
- site_name : Nom du site
- contact_email : Email de contact
- current_year : Année actuelle
                '''
            },
            {
                'name': 'Rappel d\'événement par défaut',
                'template_type': 'event_reminder',
                'subject': '🔔 Rappel : {{event.title}}{% if is_today %} - Aujourd\'hui !{% elif is_tomorrow %} - Demain{% elif days_before %} - Dans {{days_before}} jour{{days_before|pluralize}}{% endif %}',
                'html_content': '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rappel : {{event.title}}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #e74c3c; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }
        .content { background-color: #f8f9fa; padding: 30px; border-radius: 0 0 5px 5px; }
        .event-details { background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #e74c3c; }
        .urgent { background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .footer { text-align: center; margin-top: 30px; padding: 20px; background-color: #ecf0f1; border-radius: 5px; font-size: 12px; color: #7f8c8d; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{site_name}}</h1>
        <h2>🔔 Rappel d'Événement</h2>
    </div>
    
    <div class="content">
        {% if recipient_name %}
            <p>Cher(e) {{recipient_name}},</p>
        {% else %}
            <p>Bonjour,</p>
        {% endif %}
        
        {% if is_today %}
            <div class="urgent">
                <strong>⚠️ L'événement a lieu AUJOURD'HUI !</strong>
            </div>
        {% elif is_tomorrow %}
            <p>Nous vous rappelons que l'événement suivant aura lieu <strong>demain</strong> :</p>
        {% elif days_before %}
            <p>Nous vous rappelons que l'événement suivant aura lieu dans <strong>{{days_before}} jour{{days_before|pluralize}}</strong> :</p>
        {% else %}
            <p>Nous vous rappelons l'événement suivant :</p>
        {% endif %}
        
        <div class="event-details">
            <h3>{{event.title}}</h3>
            {% if event.description %}
                <p>{{event.description}}</p>
            {% endif %}
            
            <p><strong>📅 Date :</strong> {{event.start_date|date:"d/m/Y"}}</p>
            {% if event.start_time %}
                <p><strong>🕐 Heure :</strong> {{event.start_time|time:"H:i"}}</p>
            {% endif %}
            {% if event.location %}
                <p><strong>📍 Lieu :</strong> {{event.location}}</p>
            {% endif %}
        </div>
        
        <p>Nous espérons vous y voir !</p>
        
        <p>Que Dieu vous bénisse,</p>
        <p><strong>L'équipe EEBC</strong></p>
    </div>
    
    <div class="footer">
        <p>{{site_name}}<br>
        {% if contact_email %}Email: {{contact_email}}{% endif %}</p>
        <p>© {{current_year}} EEBC. Tous droits réservés.</p>
    </div>
</body>
</html>
                ''',
                'is_default': True,
                'variables_help': '''
Variables disponibles :
- event.title : Titre de l'événement
- event.description : Description de l'événement
- event.start_date : Date de début
- event.start_time : Heure de début
- event.location : Lieu de l'événement
- days_before : Nombre de jours avant l'événement
- is_today : True si l'événement est aujourd'hui
- is_tomorrow : True si l'événement est demain
- recipient_name : Nom du destinataire
                '''
            },
            {
                'name': 'Événement annulé par défaut',
                'template_type': 'event_cancelled',
                'subject': '❌ Événement annulé : {{event.title}}',
                'html_content': '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Événement annulé : {{event.title}}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #e74c3c; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }
        .content { background-color: #f8f9fa; padding: 30px; border-radius: 0 0 5px 5px; }
        .event-details { background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #e74c3c; }
        .cancellation { background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .footer { text-align: center; margin-top: 30px; padding: 20px; background-color: #ecf0f1; border-radius: 5px; font-size: 12px; color: #7f8c8d; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{site_name}}</h1>
        <h2>❌ Événement Annulé</h2>
    </div>
    
    <div class="content">
        {% if recipient_name %}
            <p>Cher(e) {{recipient_name}},</p>
        {% else %}
            <p>Bonjour,</p>
        {% endif %}
        
        <div class="cancellation">
            <strong>⚠️ Nous devons malheureusement vous informer de l'annulation de l'événement suivant :</strong>
        </div>
        
        <div class="event-details">
            <h3>{{event.title}}</h3>
            {% if event.description %}
                <p>{{event.description}}</p>
            {% endif %}
            
            <p><strong>📅 Date prévue :</strong> {{event.start_date|date:"d/m/Y"}}</p>
            {% if event.start_time %}
                <p><strong>🕐 Heure prévue :</strong> {{event.start_time|time:"H:i"}}</p>
            {% endif %}
            {% if event.location %}
                <p><strong>📍 Lieu prévu :</strong> {{event.location}}</p>
            {% endif %}
        </div>
        
        <p>Nous nous excusons pour ce désagrément et vous tiendrons informés de toute reprogrammation.</p>
        
        <p>Que Dieu vous bénisse,</p>
        <p><strong>L'équipe EEBC</strong></p>
    </div>
    
    <div class="footer">
        <p>{{site_name}}<br>
        {% if contact_email %}Email: {{contact_email}}{% endif %}</p>
        <p>© {{current_year}} EEBC. Tous droits réservés.</p>
    </div>
</body>
</html>
                ''',
                'is_default': True,
                'variables_help': '''
Variables disponibles :
- event.title : Titre de l'événement
- event.description : Description de l'événement
- event.start_date : Date de début
- event.start_time : Heure de début
- event.location : Lieu de l'événement
- recipient_name : Nom du destinataire
                '''
            },
            {
                'name': 'Confirmation de transport par défaut',
                'template_type': 'transport_confirmation',
                'subject': '🚗 Confirmation de transport - {{transport_request.destination}}',
                'html_content': '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Confirmation de transport</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #27ae60; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }
        .content { background-color: #f8f9fa; padding: 30px; border-radius: 0 0 5px 5px; }
        .transport-details { background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #27ae60; }
        .driver-info { background-color: #e8f5e8; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .footer { text-align: center; margin-top: 30px; padding: 20px; background-color: #ecf0f1; border-radius: 5px; font-size: 12px; color: #7f8c8d; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{site_name}}</h1>
        <h2>🚗 Confirmation de Transport</h2>
    </div>
    
    <div class="content">
        {% if recipient_name %}
            <p>Cher(e) {{recipient_name}},</p>
        {% else %}
            <p>Bonjour,</p>
        {% endif %}
        
        <p>Votre demande de transport a été confirmée :</p>
        
        <div class="transport-details">
            <h3>Détails du transport</h3>
            <p><strong>📍 Destination :</strong> {{transport_request.destination}}</p>
            {% if transport_request.pickup_location %}
                <p><strong>🚩 Lieu de prise en charge :</strong> {{transport_request.pickup_location}}</p>
            {% endif %}
            {% if transport_request.date %}
                <p><strong>📅 Date :</strong> {{transport_request.date|date:"d/m/Y"}}</p>
            {% endif %}
            {% if transport_request.pickup_time %}
                <p><strong>🕐 Heure de prise en charge :</strong> {{transport_request.pickup_time|time:"H:i"}}</p>
            {% endif %}
        </div>
        
        {% if has_driver and driver %}
            <div class="driver-info">
                <h4>👤 Informations du chauffeur</h4>
                <p><strong>Nom :</strong> {{driver.name}}</p>
                {% if driver.phone %}
                    <p><strong>Téléphone :</strong> {{driver.phone}}</p>
                {% endif %}
                {% if driver.vehicle_info %}
                    <p><strong>Véhicule :</strong> {{driver.vehicle_info}}</p>
                {% endif %}
            </div>
        {% else %}
            <p><em>Un chauffeur vous sera assigné prochainement. Vous recevrez une nouvelle confirmation.</em></p>
        {% endif %}
        
        <p>Merci de votre confiance.</p>
        
        <p>Que Dieu vous bénisse,</p>
        <p><strong>L'équipe EEBC</strong></p>
    </div>
    
    <div class="footer">
        <p>{{site_name}}<br>
        {% if contact_email %}Email: {{contact_email}}{% endif %}</p>
        <p>© {{current_year}} EEBC. Tous droits réservés.</p>
    </div>
</body>
</html>
                ''',
                'is_default': True,
                'variables_help': '''
Variables disponibles :
- transport_request.destination : Destination
- transport_request.pickup_location : Lieu de prise en charge
- transport_request.date : Date du transport
- transport_request.pickup_time : Heure de prise en charge
- driver.name : Nom du chauffeur
- driver.phone : Téléphone du chauffeur
- driver.vehicle_info : Informations sur le véhicule
- has_driver : True si un chauffeur est assigné
- recipient_name : Nom du passager
                '''
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for template_data in templates_data:
            template, created = EmailTemplate.objects.get_or_create(
                template_type=template_data['template_type'],
                name=template_data['name'],
                defaults=template_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Template créé: {template.name}')
                )
            else:
                # Mettre à jour le template existant
                for key, value in template_data.items():
                    setattr(template, key, value)
                template.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Template mis à jour: {template.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Terminé! {created_count} templates créés, {updated_count} mis à jour.'
            )
        )
        
        if created_count > 0 or updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    '\n💡 Les templates sont maintenant disponibles dans l\'admin Django.'
                )
            )