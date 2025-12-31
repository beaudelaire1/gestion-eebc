"""
Commande de configuration initiale de Gestion EEBC.
Crée les utilisateurs, les données de démonstration et configure le système.
Contexte : Guyane française
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal
import random

User = get_user_model()


class Command(BaseCommand):
    help = "Configure Gestion EEBC avec les données de démonstration (Guyane)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-demo-data',
            action='store_true',
            help='Ne pas créer les données de démonstration',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("[*] Configuration de Gestion EEBC (Guyane)..."))
        
        # Créer les utilisateurs
        self.create_users()
        
        if not options['no_demo_data']:
            # Créer les données de démonstration
            self.create_demo_data()
        
        self.stdout.write(self.style.SUCCESS("\n[OK] Configuration terminee avec succes!"))
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.WARNING("COMPTES CREES (MOTS DE PASSE TEMPORAIRES):"))
        self.stdout.write("="*60)
        self.stdout.write("  admin          -> admin1234")
        self.stdout.write("  responsable    -> club1234")
        self.stdout.write("  moniteur       -> moniteur1234")
        self.stdout.write("  chauffeur      -> chauffeur1234")
        self.stdout.write("  resp_groupe    -> groupe1234")
        self.stdout.write("  membre         -> user1234")
        self.stdout.write("="*60)
        self.stdout.write("\n[>] Lancez le serveur avec: python manage.py runserver")
        self.stdout.write("[>] Acces: http://127.0.0.1:8000")
        self.stdout.write("[>] Admin: http://127.0.0.1:8000/admin")

    def create_users(self):
        """Cree les utilisateurs avec leurs roles."""
        self.stdout.write("\n[+] Creation des utilisateurs...")
        
        users_data = [
            {
                'username': 'admin',
                'password': 'admin1234',
                'email': 'admin@eebc.gf',
                'first_name': 'Admin',
                'last_name': 'EEBC',
                'role': 'admin',
                'is_superuser': True,
                'is_staff': True,
            },
            {
                'username': 'responsable',
                'password': 'club1234',
                'email': 'responsable@eebc.gf',
                'first_name': 'Marie-Claire',
                'last_name': 'ALEXANDRE',
                'role': 'responsable_club',
                'is_staff': True,
            },
            {
                'username': 'moniteur',
                'password': 'moniteur1234',
                'email': 'moniteur@eebc.gf',
                'first_name': 'Jean-Louis',
                'last_name': 'CASTOR',
                'role': 'moniteur',
                'is_staff': True,
            },
            {
                'username': 'chauffeur',
                'password': 'chauffeur1234',
                'email': 'chauffeur@eebc.gf',
                'first_name': 'Patrick',
                'last_name': 'TAUBIRA',
                'role': 'chauffeur',
                'is_staff': False,
            },
            {
                'username': 'resp_groupe',
                'password': 'groupe1234',
                'email': 'groupe@eebc.gf',
                'first_name': 'Sylviane',
                'last_name': 'NELSON',
                'role': 'responsable_groupe',
                'is_staff': True,
            },
            {
                'username': 'membre',
                'password': 'user1234',
                'email': 'membre@eebc.gf',
                'first_name': 'Fabrice',
                'last_name': 'RIMANE',
                'role': 'membre',
                'is_staff': False,
            },
        ]
        
        for user_data in users_data:
            password = user_data.pop('password')
            username = user_data['username']
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults=user_data
            )
            
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f"   [+] {username} cree")
            else:
                self.stdout.write(f"   [-] {username} existe deja")

    def generate_guyane_phone(self):
        """Génère un numéro de téléphone mobile guyanais (0694)."""
        return f"0694 {random.randint(10,99)} {random.randint(10,99)} {random.randint(10,99)}"

    def create_demo_data(self):
        """Cree les donnees de demonstration pour la Guyane."""
        self.stdout.write("\n[+] Creation des donnees de demonstration (Guyane)...")
        
        # Import des modèles
        from apps.bibleclub.models import AgeGroup, BibleClass, Monitor, Child, Session
        from apps.members.models import Member
        from apps.departments.models import Department
        from apps.groups.models import Group
        from apps.events.models import EventCategory, Event
        from apps.campaigns.models import Campaign, Donation
        from apps.transport.models import DriverProfile
        from apps.inventory.models import Category, Equipment
        from apps.communication.models import Announcement
        
        # Villes de Guyane
        villes_guyane = ['Cayenne', 'Matoury', 'Remire-Montjoly', 'Kourou', 'Saint-Laurent-du-Maroni', 'Macouria']
        
        # Tranches d'age
        self.stdout.write("   -> Tranches d'age...")
        age_groups = [
            {'name': 'Petits', 'min_age': 3, 'max_age': 5, 'color': '#f59e0b'},
            {'name': 'Moyens', 'min_age': 6, 'max_age': 8, 'color': '#10b981'},
            {'name': 'Grands', 'min_age': 9, 'max_age': 12, 'color': '#3b82f6'},
        ]
        for ag_data in age_groups:
            AgeGroup.objects.get_or_create(name=ag_data['name'], defaults=ag_data)
        
        # Classes
        self.stdout.write("   -> Classes...")
        for ag in AgeGroup.objects.all():
            BibleClass.objects.get_or_create(
                age_group=ag,
                defaults={'room': f"Salle {ag.min_age}", 'max_capacity': 15}
            )
        
        # Moniteurs
        self.stdout.write("   -> Moniteurs...")
        moniteur_user = User.objects.filter(username='moniteur').first()
        responsable_user = User.objects.filter(username='responsable').first()
        
        if moniteur_user:
            first_class = BibleClass.objects.first()
            Monitor.objects.get_or_create(
                user=moniteur_user,
                defaults={'bible_class': first_class, 'is_lead': False, 'phone': self.generate_guyane_phone()}
            )
        
        if responsable_user:
            Monitor.objects.get_or_create(
                user=responsable_user,
                defaults={'bible_class': BibleClass.objects.first(), 'is_lead': True, 'phone': self.generate_guyane_phone()}
            )
        
        # Enfants - Noms typiques de Guyane
        self.stdout.write("   -> Enfants...")
        children_data = [
            {'first_name': 'Kenzo', 'last_name': 'CASTOR', 'gender': 'M', 'age_offset': 4},
            {'first_name': 'Maelys', 'last_name': 'NELSON', 'gender': 'F', 'age_offset': 5},
            {'first_name': 'Lenny', 'last_name': 'ALEXANDRE', 'gender': 'M', 'age_offset': 7},
            {'first_name': 'Anais', 'last_name': 'TAUBIRA', 'gender': 'F', 'age_offset': 6},
            {'first_name': 'Mathis', 'last_name': 'RIMANE', 'gender': 'M', 'age_offset': 10},
            {'first_name': 'Louna', 'last_name': 'ZENON', 'gender': 'F', 'age_offset': 9},
            {'first_name': 'Ethan', 'last_name': 'CESAIRE', 'gender': 'M', 'age_offset': 11},
            {'first_name': 'Jade', 'last_name': 'PAULIN', 'gender': 'F', 'age_offset': 8},
            {'first_name': 'Noah', 'last_name': 'BERTHELOT', 'gender': 'M', 'age_offset': 3},
            {'first_name': 'Emma', 'last_name': 'JEAN-LOUIS', 'gender': 'F', 'age_offset': 4},
        ]
        
        for child_data in children_data:
            age = child_data.pop('age_offset')
            dob = date.today() - timedelta(days=age*365 + random.randint(0, 365))
            
            # Trouver la bonne classe
            age_group = AgeGroup.objects.filter(min_age__lte=age, max_age__gte=age).first()
            bible_class = BibleClass.objects.filter(age_group=age_group).first() if age_group else None
            
            Child.objects.get_or_create(
                first_name=child_data['first_name'],
                last_name=child_data['last_name'],
                defaults={
                    **child_data,
                    'date_of_birth': dob,
                    'bible_class': bible_class,
                    'parent1_name': f"M. et Mme {child_data['last_name']}",
                    'parent1_phone': self.generate_guyane_phone(),
                    'pickup_address': f"{random.randint(1, 150)} rue des Palmistes, {random.choice(['Cayenne', 'Matoury', 'Remire-Montjoly'])}",
                }
            )
        
        # Membres - Noms guyanais
        self.stdout.write("   -> Membres...")
        members_data = [
            {'first_name': 'Jacques', 'last_name': 'APPOLINAIRE', 'gender': 'M', 'status': 'actif', 'is_baptized': True},
            {'first_name': 'Christiane', 'last_name': 'MARTHELY', 'gender': 'F', 'status': 'actif', 'is_baptized': True},
            {'first_name': 'Serge', 'last_name': 'PINDARD', 'gender': 'M', 'status': 'actif', 'is_baptized': False},
            {'first_name': 'Lucienne', 'last_name': 'JEAN-CHARLES', 'gender': 'F', 'status': 'visiteur', 'is_baptized': False},
            {'first_name': 'Yannick', 'last_name': 'MATHURIN', 'gender': 'M', 'status': 'actif', 'is_baptized': True},
        ]
        
        for member_data in members_data:
            Member.objects.get_or_create(
                first_name=member_data['first_name'],
                last_name=member_data['last_name'],
                defaults={
                    **member_data,
                    'email': f"{member_data['first_name'].lower()}.{member_data['last_name'].lower().replace('-', '')}@gmail.com",
                    'phone': self.generate_guyane_phone(),
                    'city': random.choice(villes_guyane),
                    'date_joined': date.today() - timedelta(days=random.randint(100, 1000)),
                }
            )
        
        # Departements
        self.stdout.write("   -> Departements...")
        departments = ['Louange', 'Accueil', 'Sonorisation', 'Restauration', 'Entretien']
        for dept_name in departments:
            Department.objects.get_or_create(
                name=dept_name,
                defaults={'description': f"Département {dept_name} de l'église EEBC Guyane"}
            )
        
        # Groupes
        self.stdout.write("   -> Groupes...")
        groups_data = [
            {'name': 'Jeunesse EEBC Guyane', 'group_type': 'youth', 'meeting_day': 'saturday', 'color': '#8b5cf6'},
            {'name': 'Chorale Gospel', 'group_type': 'choir', 'meeting_day': 'thursday', 'color': '#ec4899'},
            {'name': 'The Ray of Sunshine', 'group_type': 'service', 'meeting_day': 'wednesday', 'color': '#f59e0b'},
            {'name': 'Groupe de prière', 'group_type': 'prayer', 'meeting_day': 'tuesday', 'color': '#10b981'},
        ]
        for group_data in groups_data:
            Group.objects.get_or_create(name=group_data['name'], defaults=group_data)
        
        # Categories d'evenements
        self.stdout.write("   -> Categories d'evenements...")
        event_categories = [
            {'name': 'Culte', 'color': '#3b82f6'},
            {'name': 'Club Biblique', 'color': '#10b981'},
            {'name': 'Réunion de prière', 'color': '#8b5cf6'},
            {'name': 'Événement spécial', 'color': '#f59e0b'},
            {'name': 'Formation', 'color': '#ec4899'},
        ]
        for cat_data in event_categories:
            EventCategory.objects.get_or_create(name=cat_data['name'], defaults=cat_data)
        
        # Evenements
        self.stdout.write("   -> Evenements...")
        culte_cat = EventCategory.objects.filter(name='Culte').first()
        club_cat = EventCategory.objects.filter(name='Club Biblique').first()
        
        # Prochains dimanches
        today = date.today()
        next_sunday = today + timedelta(days=(6 - today.weekday()) % 7)
        if next_sunday == today:
            next_sunday += timedelta(days=7)
        
        for i in range(4):
            event_date = next_sunday + timedelta(weeks=i)
            Event.objects.get_or_create(
                title=f"Culte dominical",
                start_date=event_date,
                defaults={
                    'category': culte_cat,
                    'start_time': '09:00',
                    'end_time': '11:30',
                    'location': 'Temple EEBC - Cayenne',
                    'visibility': 'public',
                    'recurrence': 'weekly',
                }
            )
            Event.objects.get_or_create(
                title=f"Club Biblique",
                start_date=event_date,
                defaults={
                    'category': club_cat,
                    'start_time': '09:00',
                    'end_time': '10:30',
                    'location': 'Salles enfants - Cayenne',
                    'visibility': 'members',
                }
            )
        
        # Campagnes
        self.stdout.write("   -> Campagnes...")
        Campaign.objects.get_or_create(
            name="Rénovation du temple",
            defaults={
                'description': "Collecte pour la rénovation de la toiture et la climatisation du temple de Cayenne.",
                'goal_amount': Decimal('25000.00'),
                'collected_amount': Decimal('12500.00'),
                'start_date': today - timedelta(days=30),
                'end_date': today + timedelta(days=60),
                'is_active': True,
            }
        )
        Campaign.objects.get_or_create(
            name="Matériel Club Biblique",
            defaults={
                'description': "Achat de nouveau matériel pédagogique pour les enfants du Club Biblique.",
                'goal_amount': Decimal('3000.00'),
                'collected_amount': Decimal('2650.00'),
                'start_date': today - timedelta(days=15),
                'end_date': today + timedelta(days=15),
                'is_active': True,
            }
        )
        
        # Chauffeur
        self.stdout.write("   -> Chauffeurs...")
        chauffeur_user = User.objects.filter(username='chauffeur').first()
        if chauffeur_user:
            DriverProfile.objects.get_or_create(
                user=chauffeur_user,
                defaults={
                    'vehicle_type': 'Monospace',
                    'vehicle_model': 'Toyota Innova',
                    'capacity': 7,
                    'zone': 'Cayenne - Matoury - Remire',
                    'is_available': True,
                    'available_sunday': True,
                }
            )
        
        # Inventaire
        self.stdout.write("   -> Inventaire...")
        cat_audio, _ = Category.objects.get_or_create(name='Audio')
        cat_mobilier, _ = Category.objects.get_or_create(name='Mobilier')
        cat_pedagogique, _ = Category.objects.get_or_create(name='Matériel pédagogique')
        cat_climatisation, _ = Category.objects.get_or_create(name='Climatisation')
        
        Equipment.objects.get_or_create(
            name='Microphone sans fil',
            defaults={'category': cat_audio, 'quantity': 4, 'condition': 'good', 'location': 'Régie'}
        )
        Equipment.objects.get_or_create(
            name='Ventilateurs',
            defaults={'category': cat_climatisation, 'quantity': 8, 'condition': 'good', 'location': 'Temple'}
        )
        Equipment.objects.get_or_create(
            name='Climatiseur split',
            defaults={'category': cat_climatisation, 'quantity': 3, 'condition': 'good', 'location': 'Salles enfants'}
        )
        Equipment.objects.get_or_create(
            name='Tables pliantes',
            defaults={'category': cat_mobilier, 'quantity': 12, 'condition': 'good', 'location': 'Carbet'}
        )
        Equipment.objects.get_or_create(
            name='Tableau blanc',
            defaults={'category': cat_pedagogique, 'quantity': 3, 'condition': 'new', 'location': 'Salles enfants'}
        )
        
        # Annonces
        self.stdout.write("   -> Annonces...")
        admin_user = User.objects.filter(username='admin').first()
        Announcement.objects.get_or_create(
            title="Bienvenue sur Gestion EEBC Guyane!",
            defaults={
                'content': "Le nouveau système de gestion de l'église EEBC Guyane est maintenant opérationnel. Bonne utilisation à tous!",
                'is_active': True,
                'is_pinned': True,
                'author': admin_user,
            }
        )
        
        self.stdout.write("   [OK] Donnees de demonstration creees pour la Guyane")
