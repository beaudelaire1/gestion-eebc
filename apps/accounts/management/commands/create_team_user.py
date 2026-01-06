"""
Commande pour créer un utilisateur via l'équipe depuis la ligne de commande.
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from apps.accounts.user_creation import create_user_by_team

User = get_user_model()


class Command(BaseCommand):
    help = 'Crée un nouvel utilisateur avec identifiants générés automatiquement'

    def add_arguments(self, parser):
        parser.add_argument('first_name', type=str, help='Prénom de l\'utilisateur')
        parser.add_argument('last_name', type=str, help='Nom de l\'utilisateur')
        parser.add_argument('email', type=str, help='Email de l\'utilisateur')
        
        parser.add_argument(
            '--role',
            type=str,
            default='membre',
            choices=[choice[0] for choice in User.Role.choices],
            help='Rôle de l\'utilisateur (défaut: membre)'
        )
        
        parser.add_argument(
            '--phone',
            type=str,
            default='',
            help='Numéro de téléphone (optionnel)'
        )
        
        parser.add_argument(
            '--created-by',
            type=str,
            help='Username de l\'utilisateur qui crée le compte (défaut: premier admin trouvé)'
        )
        
        parser.add_argument(
            '--no-email',
            action='store_true',
            help='Ne pas envoyer l\'email d\'invitation'
        )

    def handle(self, *args, **options):
        first_name = options['first_name'].strip().title()
        last_name = options['last_name'].strip().upper()
        email = options['email'].strip().lower()
        role = options['role']
        phone = options['phone']
        
        # Vérifier que l'email n'existe pas déjà
        if User.objects.filter(email=email).exists():
            raise CommandError(f'Un utilisateur avec l\'email {email} existe déjà.')
        
        # Trouver l'utilisateur créateur
        created_by_username = options.get('created_by')
        if created_by_username:
            try:
                created_by = User.objects.get(username=created_by_username)
            except User.DoesNotExist:
                raise CommandError(f'Utilisateur créateur "{created_by_username}" non trouvé.')
        else:
            # Prendre le premier admin disponible
            created_by = User.objects.filter(
                models.Q(is_superuser=True) | models.Q(role=User.Role.ADMIN)
            ).first()
            
            if not created_by:
                raise CommandError('Aucun administrateur trouvé pour créer le compte.')
        
        self.stdout.write(f'Création de l\'utilisateur {first_name} {last_name}...')
        
        # Créer l'utilisateur
        user, username, password = create_user_by_team(
            first_name=first_name,
            last_name=last_name,
            email=email,
            role=role,
            phone=phone,
            created_by=created_by
        )
        
        if user:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Utilisateur créé avec succès !')
            )
            self.stdout.write(f'  Nom complet: {user.get_full_name()}')
            self.stdout.write(f'  Username: {username}')
            self.stdout.write(f'  Email: {user.email}')
            self.stdout.write(f'  Rôle: {user.get_role_display()}')
            self.stdout.write(f'  Créé par: {created_by.get_full_name()}')
            
            if not options['no_email']:
                self.stdout.write(f'  📧 Email d\'invitation envoyé à {user.email}')
            else:
                self.stdout.write(f'  ⚠️  Email d\'invitation non envoyé (--no-email)')
                self.stdout.write(f'  🔑 Mot de passe temporaire: {password}')
            
        else:
            raise CommandError('Erreur lors de la création de l\'utilisateur.')


# Import nécessaire pour les requêtes
from django.db import models