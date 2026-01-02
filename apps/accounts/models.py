from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Modèle utilisateur personnalisé pour Gestion EEBC.
    Permet d'ajouter des rôles et des informations supplémentaires.
    """
    
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrateur'
        RESPONSABLE_CLUB = 'responsable_club', 'Responsable Club Biblique'
        MONITEUR = 'moniteur', 'Moniteur'
        CHAUFFEUR = 'chauffeur', 'Chauffeur'
        RESPONSABLE_GROUPE = 'responsable_groupe', 'Responsable de Groupe'
        SECRETARIAT = 'secretariat', 'Secrétariat'
        FINANCE = 'finance', 'Finance'
        ENCADRANT = 'encadrant', 'Encadrant'
        MEMBRE = 'membre', 'Membre'
    
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBRE,
        verbose_name="Rôle"
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
    
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser
    
    @property
    def is_responsable_club(self):
        return self.role == self.Role.RESPONSABLE_CLUB or self.is_admin
    
    @property
    def is_moniteur(self):
        return self.role == self.Role.MONITEUR or self.is_responsable_club
    
    @property
    def is_chauffeur(self):
        return self.role == self.Role.CHAUFFEUR or self.is_admin
    
    @property
    def is_responsable_groupe(self):
        return self.role == self.Role.RESPONSABLE_GROUPE or self.is_admin
    
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

