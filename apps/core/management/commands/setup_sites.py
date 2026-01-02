"""
Commande pour initialiser les sites Cabassou et Macouria.
"""
from django.core.management.base import BaseCommand
from apps.core.models import Site, City, Neighborhood


class Command(BaseCommand):
    help = 'Initialise les sites Cabassou et Macouria avec les villes et quartiers de Guyane'

    def handle(self, *args, **options):
        self.stdout.write('Création des sites...')
        
        # Créer le site Cabassou (principal)
        cabassou, created = Site.objects.update_or_create(
            code='CAB',
            defaults={
                'name': 'EEBC Cabassou',
                'address': '5 rue Calimbés 2, Route de Cabassou',
                'city': 'Cayenne',
                'postal_code': '97300',
                'worship_schedule': '''Culte: Dimanche 9h30-12h00
Étude biblique: Mercredi 19h00
Réunion de prière: Vendredi 19h00
Groupe de jeunes: Samedi 16h00-18h00
Club biblique: Dimanche 15h00-16h30''',
                'is_main_site': True,
                'is_active': True,
                'latitude': 4.9225,
                'longitude': -52.3058,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Site créé: {cabassou}'))
        else:
            self.stdout.write(f'  → Site mis à jour: {cabassou}')
        
        # Créer le site Macouria
        macouria, created = Site.objects.update_or_create(
            code='MAC',
            defaults={
                'name': 'EEBC Macouria',
                'address': 'Macouria',
                'city': 'Macouria',
                'postal_code': '97355',
                'worship_schedule': 'Dimanche 10h00',
                'is_main_site': False,
                'is_active': True,
                'latitude': 4.9167,
                'longitude': -52.3667,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Site créé: {macouria}'))
        else:
            self.stdout.write(f'  → Site mis à jour: {macouria}')
        
        self.stdout.write('')
        self.stdout.write('Création des villes...')
        
        # Villes de Guyane
        cities_data = [
            {'name': 'Cayenne', 'postal_code': '97300', 'latitude': 4.9333, 'longitude': -52.3333},
            {'name': 'Matoury', 'postal_code': '97351', 'latitude': 4.8500, 'longitude': -52.3333},
            {'name': 'Rémire-Montjoly', 'postal_code': '97354', 'latitude': 4.8833, 'longitude': -52.2667},
            {'name': 'Macouria', 'postal_code': '97355', 'latitude': 4.9167, 'longitude': -52.3667},
            {'name': 'Kourou', 'postal_code': '97310', 'latitude': 5.1667, 'longitude': -52.6500},
            {'name': 'Saint-Laurent-du-Maroni', 'postal_code': '97320', 'latitude': 5.5000, 'longitude': -54.0333},
        ]
        
        cities = {}
        for city_data in cities_data:
            city, created = City.objects.update_or_create(
                name=city_data['name'],
                defaults=city_data
            )
            cities[city_data['name']] = city
            status = '✓ Créée' if created else '→ Mise à jour'
            self.stdout.write(f'  {status}: {city}')
        
        self.stdout.write('')
        self.stdout.write('Création des quartiers...')
        
        # Quartiers par ville (liste complète)
        neighborhoods_data = {
            'Cayenne': [
                'Centre-Ville',
                'Baduel',
                'Montabo',
                'Mont-Lucas',
                'Cabassou',
                'Bonhomme',
                'Cité Zéphir',
                'La Crique',
                'Amandiers',
                'Raban',
                'Tigre',
                'Chatenay',
                'Hibiscus',
            ],
            'Matoury': [
                'Matoury Bourg',
                'Cogneau-Lamirande',
                'Balata',
                'La Chaumière',
                'Petit La Chaumière',
                'Degrad Samary',
                'Saramaka',
                'Larivot',
                'Soula',
                'Copaya',
                'Sainte-Rita',
                'Stoupan',
                'Providence',
                'Concorde',
            ],
            'Rémire-Montjoly': [
                'Montjoly',
                'Rémire',
                'Vidal',
                'Rorota',
                'Loyola',
            ],
            'Macouria': [
                'Tonate',
                'Soula',
                'Matiti',
                'Sablance',
            ],
        }
        
        for city_name, neighborhoods in neighborhoods_data.items():
            if city_name in cities:
                city = cities[city_name]
                for neighborhood_name in neighborhoods:
                    neighborhood, created = Neighborhood.objects.update_or_create(
                        name=neighborhood_name,
                        city=city,
                        defaults={'is_active': True}
                    )
                    status = '✓' if created else '→'
                    self.stdout.write(f'  {status} {neighborhood}')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Configuration des sites terminée !'))
        self.stdout.write(f'  - {Site.objects.count()} sites')
        self.stdout.write(f'  - {City.objects.count()} villes')
        self.stdout.write(f'  - {Neighborhood.objects.count()} quartiers')
        self.stdout.write('')
        self.stdout.write('Note: Vous pouvez ajouter de nouveaux quartiers via l\'interface admin.')
