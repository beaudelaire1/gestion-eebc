from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import secrets


class User(AbstractUser):
    """
    Modèle utilisateur personnalisé pour Gestion EEBC.
    Permet d'ajouter des rôles et des informations supplémentaires.
    """
    
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrateur'
        PASTEUR = 'pasteur', 'Pasteur'
        ANCIEN = 'ancien', 'Ancien'
        DIACRE = 'diacre', 'Diacre'
        RESPONSABLE_CLUB = 'responsable_club', 'Responsable Club Biblique'
        MONITEUR = 'moniteur', 'Moniteur'
        CHAUFFEUR = 'chauffeur', 'Chauffeur'
        RESPONSABLE_GROUPE = 'responsable_groupe', 'Responsable de Groupe'
        SECRETARIAT = 'secretariat', 'Secrétariat'
        FINANCE = 'finance', 'Finance'
        ENCADRANT = 'encadrant', 'Encadrant'
        MEMBRE = 'membre', 'Membre'
    
    # Changer role en TextField pour permettre plusieurs rôles séparés par des virgules
    role = models.TextField(
        default=Role.MEMBRE,
        verbose_name="Rôles",
        help_text="Rôles séparés par des virgules (ex: pasteur,ancien)"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Téléphone"
    )
    photo = models.ImageField(
        upload_to='users/photos/',
        blank=True,
        null=True,
        verbose_name="Photo"
    )
    date_joined_church = models.DateField(
        blank=True,
        null=True,
        verbose_name="Date d'arrivée à l'église"
    )
    
    # Compte créé par l'équipe
    created_by_team = models.BooleanField(
        default=False,
        verbose_name="Créé par l'équipe",
        help_text="Indique si ce compte a été créé par un membre de l'équipe"
    )
    
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_users',
        verbose_name="Créé par"
    )
    
    # Forcer le changement de mot de passe
    must_change_password = models.BooleanField(
        default=False,
        verbose_name="Doit changer le mot de passe",
        help_text="Force l'utilisateur à changer son mot de passe à la prochaine connexion"
    )
    
    # =========================================================================
    # RATE LIMITING - Protection contre les attaques par force brute
    # =========================================================================
    failed_login_attempts = models.PositiveIntegerField(
        default=0,
        verbose_name="Tentatives de connexion échouées"
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Verrouillé jusqu'à"
    )
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Dernière IP de connexion"
    )
    
    # =========================================================================
    # DOUBLE AUTHENTIFICATION (2FA)
    # =========================================================================
    two_factor_enabled = models.BooleanField(
        default=False,
        verbose_name="2FA activé"
    )
    two_factor_secret = models.CharField(
        max_length=32,
        blank=True,
        verbose_name="Clé secrète 2FA",
        help_text="Clé TOTP pour Google Authenticator"
    )
    two_factor_backup_codes = models.TextField(
        blank=True,
        verbose_name="Codes de secours",
        help_text="Codes de secours hashés (JSON)"
    )
    two_factor_confirmed = models.BooleanField(
        default=False,
        verbose_name="2FA confirmé",
        help_text="L'utilisateur a confirmé la configuration 2FA"
    )
    
    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ['last_name', 'first_name']
    
    def __str__(self):
        return f"{self.get_full_name() or self.username}"
    
    def get_roles_list(self):
        """Retourne la liste des rôles de l'utilisateur."""
        if not self.role:
            return [self.Role.MEMBRE]
        return [role.strip() for role in self.role.split(',') if role.strip()]
    
    def has_role(self, role):
        """Vérifie si l'utilisateur a un rôle spécifique."""
        return role in self.get_roles_list()
    
    def add_role(self, role):
        """Ajoute un rôle à l'utilisateur."""
        roles = self.get_roles_list()
        if role not in roles:
            roles.append(role)
            self.role = ','.join(roles)
            self.save(update_fields=['role'])
    
    def remove_role(self, role):
        """Supprime un rôle de l'utilisateur."""
        roles = self.get_roles_list()
        if role in roles:
            roles.remove(role)
            self.role = ','.join(roles) if roles else self.Role.MEMBRE
            self.save(update_fields=['role'])
    
    def get_role_display(self):
        """Retourne l'affichage des rôles."""
        roles = self.get_roles_list()
        role_labels = []
        for role in roles:
            for choice_value, choice_label in self.Role.choices:
                if choice_value == role:
                    role_labels.append(choice_label)
                    break
        return ', '.join(role_labels)
    
    @property
    def is_admin(self):
        return self.has_role(self.Role.ADMIN) or self.is_superuser
    
    @property
    def is_pasteur(self):
        return self.has_role(self.Role.PASTEUR) or self.is_admin
    
    @property
    def is_ancien(self):
        return self.has_role(self.Role.ANCIEN) or self.is_pasteur
    
    @property
    def is_diacre(self):
        return self.has_role(self.Role.DIACRE) or self.is_ancien
    
    @property
    def is_responsable_club(self):
        return self.has_role(self.Role.RESPONSABLE_CLUB) or self.is_admin
    
    @property
    def is_moniteur(self):
        return self.has_role(self.Role.MONITEUR) or self.is_responsable_club
    
    @property
    def is_chauffeur(self):
        return self.has_role(self.Role.CHAUFFEUR) or self.is_admin
    
    @property
    def is_responsable_groupe(self):
        return self.has_role(self.Role.RESPONSABLE_GROUPE) or self.is_admin
    
    @property
    def can_view_member_alerts(self):
        """Vérifie si l'utilisateur peut voir les alertes de membres non visités."""
        return (self.is_pasteur or self.is_ancien or self.is_diacre or self.is_admin)
    
    # =========================================================================
    # MÉTHODES 2FA
    # =========================================================================
    def setup_two_factor(self):
        """Initialise la configuration 2FA."""
        from .two_factor import generate_totp_secret, generate_backup_codes, hash_backup_code
        import json
        
        self.two_factor_secret = generate_totp_secret()
        
        # Générer et hasher les codes de secours
        backup_codes = generate_backup_codes(10)
        hashed_codes = [hash_backup_code(code) for code in backup_codes]
        self.two_factor_backup_codes = json.dumps(hashed_codes)
        
        self.two_factor_confirmed = False
        self.save()
        
        return backup_codes  # Retourner les codes en clair pour affichage unique
    
    def get_totp_qr_code(self):
        """Génère le QR code pour configuration."""
        from .two_factor import get_totp_uri, generate_qr_code
        
        if not self.two_factor_secret:
            return None
        
        uri = get_totp_uri(self, self.two_factor_secret)
        return generate_qr_code(uri)
    
    def verify_two_factor_code(self, code):
        """Vérifie un code 2FA (TOTP ou code de secours)."""
        from .two_factor import verify_totp, hash_backup_code
        import json
        
        if not self.two_factor_enabled:
            return True
        
        # Essayer TOTP d'abord
        if verify_totp(self.two_factor_secret, code):
            return True
        
        # Essayer les codes de secours
        if self.two_factor_backup_codes:
            hashed_input = hash_backup_code(code.upper().replace(' ', ''))
            backup_codes = json.loads(self.two_factor_backup_codes)
            
            if hashed_input in backup_codes:
                # Supprimer le code utilisé
                backup_codes.remove(hashed_input)
                self.two_factor_backup_codes = json.dumps(backup_codes)
                self.save()
                return True
        
        return False
    
    def confirm_two_factor(self, code):
        """Confirme et active la 2FA après vérification du premier code."""
        from .two_factor import verify_totp
        
        if verify_totp(self.two_factor_secret, code):
            self.two_factor_enabled = True
            self.two_factor_confirmed = True
            self.save()
            return True
        return False
    
    def disable_two_factor(self):
        """Désactive la 2FA."""
        self.two_factor_enabled = False
        self.two_factor_secret = ''
        self.two_factor_backup_codes = ''
        self.two_factor_confirmed = False
        self.save()
    
    def is_locked(self):
        """Vérifie si le compte est verrouillé."""
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False
    
    def reset_failed_attempts(self):
        """Réinitialise les tentatives échouées."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=['failed_login_attempts', 'locked_until'])
    
    def record_failed_attempt(self, lockout_minutes=15, max_attempts=5):
        """Enregistre une tentative de connexion échouée."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=lockout_minutes)
        self.save(update_fields=['failed_login_attempts', 'locked_until'])


class PasswordChangeToken(models.Model):
    """
    Token sécurisé pour le flux de changement de mot de passe initial.
    Utilisé à la place du stockage du mot de passe en session.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_change_tokens',
        verbose_name="Utilisateur"
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="Token"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Créé le"
    )
    used = models.BooleanField(
        default=False,
        verbose_name="Utilisé"
    )
    expires_at = models.DateTimeField(
        verbose_name="Expire le"
    )
    
    class Meta:
        verbose_name = "Token de changement de mot de passe"
        verbose_name_plural = "Tokens de changement de mot de passe"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Token pour {self.user} - {'Utilisé' if self.used else 'Actif'}"
    
    def is_valid(self):
        """Vérifie si le token est valide (non utilisé et non expiré)."""
        return not self.used and timezone.now() < self.expires_at
    
    def mark_as_used(self):
        """Marque le token comme utilisé."""
        self.used = True
        self.save(update_fields=['used'])
    
    @classmethod
    def generate_token(cls):
        """Génère un token sécurisé."""
        return secrets.token_urlsafe(48)

