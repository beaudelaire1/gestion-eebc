"""
Commande pour lister les utilisateurs existants.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = 'Liste tous les utilisateurs avec leurs informations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--role',
            type=str,
            choices=[choice[0] for choice in User.Role.choices],
            help='Filtrer par rôle'
        )
        
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Afficher seulement les utilisateurs actifs'
        )
        
        parser.add_argument(
            '--inactive-only',
            action='store_true',
            help='Afficher seulement les utilisateurs inactifs'
        )
        
        parser.add_argument(
            '--created-by-team',
            action='store_true',
            help='Afficher seulement les utilisateurs créés par l\'équipe'
        )

    def handle(self, *args, **options):
        # Construire la requête
        queryset = User.objects.all()
        
        if options['role']:
            queryset = queryset.filter(role=options['role'])
        
        if options['created_by_team']:
            queryset = queryset.filter(created_by_team=True)
        
        # Filtrer par statut d'activation
        if options['active_only']:
            active_users = []
            for user in queryset:
                if user.has_usable_password():
                    active_users.append(user)
            users = active_users
        elif options['inactive_only']:
            inactive_users = []
            for user in queryset:
                if not user.has_usable_password():
                    inactive_users.append(user)
            users = inactive_users
        else:
            users = list(queryset.order_by('last_name', 'first_name'))
        
        if not users:
            self.stdout.write(
                self.style.WARNING('Aucun utilisateur trouvé avec ces critères.')
            )
            return
        
        # Afficher l'en-tête
        self.stdout.write(
            self.style.SUCCESS(f'\n📋 {len(users)} utilisateur(s) trouvé(s)\n')
        )
        
        # Afficher les utilisateurs
        for user in users:
            status = "✅ Actif" if user.has_usable_password() else "⏳ En attente"
            created_by_info = ""
            
            if user.created_by_team and user.created_by:
                created_by_info = f" (créé par {user.created_by.get_full_name()})"
            
            last_login = "Jamais"
            if user.last_login:
                last_login = user.last_login.strftime("%d/%m/%Y %H:%M")
            
            self.stdout.write(f"👤 {user.get_full_name()}")
            self.stdout.write(f"   📧 {user.email}")
            self.stdout.write(f"   🔑 @{user.username}")
            self.stdout.write(f"   🎭 {user.get_role_display()}")
            self.stdout.write(f"   📊 {status}")
            self.stdout.write(f"   🕐 Dernière connexion: {last_login}")
            
            if created_by_info:
                self.stdout.write(f"   👥 {created_by_info}")
            
            self.stdout.write("")  # Ligne vide
        
        # Statistiques
        total_users = len(users)
        active_count = sum(1 for u in users if u.has_usable_password())
        inactive_count = total_users - active_count
        team_created = sum(1 for u in users if u.created_by_team)
        
        self.stdout.write("📊 Statistiques:")
        self.stdout.write(f"   Total: {total_users}")
        self.stdout.write(f"   Actifs: {active_count}")
        self.stdout.write(f"   En attente: {inactive_count}")
        self.stdout.write(f"   Créés par l'équipe: {team_created}")
        
        # Répartition par rôle
        roles = {}
        for user in users:
            role_display = user.get_role_display()
            roles[role_display] = roles.get(role_display, 0) + 1
        
        if roles:
            self.stdout.write("\n🎭 Répartition par rôle:")
            for role, count in sorted(roles.items()):
                self.stdout.write(f"   {role}: {count}")