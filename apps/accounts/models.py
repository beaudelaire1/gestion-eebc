import json
import secrets

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Utilisateur personnalisé pour Gestion EEBC."""

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

    role = models.TextField(
        default=Role.MEMBRE,
        verbose_name="Rôles",
        help_text="Rôles séparés par des virgules (ex: pasteur,ancien)",
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    photo = models.ImageField(
        upload_to='users/photos/', blank=True, null=True, verbose_name="Photo"
    )
    date_joined_church = models.DateField(
        blank=True, null=True, verbose_name="Date d'arrivée à l'église"
    )

    created_by_team = models.BooleanField(
        default=False,
        verbose_name="Créé par l'équipe",
        help_text="Indique si ce compte a été créé par un membre de l'équipe",
    )
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users',
        verbose_name="Créé par",
    )
    must_change_password = models.BooleanField(
        default=False,
        verbose_name="Doit changer le mot de passe",
        help_text="Force l'utilisateur à changer son mot de passe à la prochaine connexion",
    )

    # Rate limiting / verrouillage du compte.
    failed_login_attempts = models.PositiveIntegerField(
        default=0, verbose_name="Tentatives de connexion échouées"
    )
    locked_until = models.DateTimeField(
        null=True, blank=True, verbose_name="Verrouillé jusqu'à"
    )
    last_login_ip = models.GenericIPAddressField(
        null=True, blank=True, verbose_name="Dernière IP de connexion"
    )

    # Double authentification.
    two_factor_enabled = models.BooleanField(default=False, verbose_name="2FA activé")
    two_factor_secret = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Clé secrète 2FA",
        help_text="Secret TOTP chiffré au repos",
    )
    two_factor_backup_codes = models.TextField(
        blank=True,
        verbose_name="Codes de secours",
        help_text="Codes de secours hashés (JSON)",
    )
    two_factor_confirmed = models.BooleanField(
        default=False,
        verbose_name="2FA confirmé",
        help_text="L'utilisateur a confirmé la configuration 2FA",
    )

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.get_full_name() or self.username}"

    def get_roles_list(self):
        if not self.role:
            return [self.Role.MEMBRE]
        return [role.strip() for role in self.role.split(',') if role.strip()]

    def has_role(self, role):
        return role in self.get_roles_list()

    def has_any_role(self, *roles):
        user_roles = self.get_roles_list()
        return any(role in user_roles for role in roles)

    def add_role(self, role):
        roles = self.get_roles_list()
        if role not in roles:
            roles.append(role)
            self.role = ','.join(roles)
            self.save(update_fields=['role'])

    def remove_role(self, role):
        roles = self.get_roles_list()
        if role in roles:
            roles.remove(role)
            self.role = ','.join(roles) if roles else self.Role.MEMBRE
            self.save(update_fields=['role'])

    def get_role_display(self):
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
        return self.is_pasteur or self.is_ancien or self.is_diacre or self.is_admin

    @property
    def is_two_factor_required(self):
        from .two_factor_security import requires_two_factor

        return requires_two_factor(self)

    # =========================================================================
    # DOUBLE AUTHENTIFICATION (2FA)
    # =========================================================================
    def get_two_factor_secret(self, migrate_plaintext=True):
        """Retourne le secret TOTP en clair et chiffre les anciennes valeurs au repos."""
        from .two_factor_security import (
            decrypt_totp_secret,
            encrypt_totp_secret,
            is_encrypted_secret,
        )

        if not self.two_factor_secret:
            return ''

        stored_secret = self.two_factor_secret
        secret = decrypt_totp_secret(stored_secret)
        if migrate_plaintext and not is_encrypted_secret(stored_secret):
            self.two_factor_secret = encrypt_totp_secret(secret)
            self.save(update_fields=['two_factor_secret'])
        return secret

    def setup_two_factor(self):
        """Initialise une nouvelle configuration TOTP et ses codes de secours."""
        from .two_factor import generate_backup_codes, generate_totp_secret, hash_backup_code
        from .two_factor_security import encrypt_totp_secret

        secret = generate_totp_secret()
        self.two_factor_secret = encrypt_totp_secret(secret)

        backup_codes = generate_backup_codes(10)
        self.two_factor_backup_codes = json.dumps(
            [hash_backup_code(code) for code in backup_codes]
        )
        self.two_factor_enabled = False
        self.two_factor_confirmed = False
        self.save(
            update_fields=[
                'two_factor_secret',
                'two_factor_backup_codes',
                'two_factor_enabled',
                'two_factor_confirmed',
            ]
        )
        return backup_codes

    def get_totp_qr_code(self):
        from .two_factor import generate_qr_code, get_totp_uri

        secret = self.get_two_factor_secret()
        if not secret:
            return None
        return generate_qr_code(get_totp_uri(self, secret))

    def verify_two_factor_code(self, code):
        """Vérifie un code TOTP ou un code de secours à usage unique."""
        from .two_factor import hash_backup_code, verify_totp

        if not self.two_factor_enabled or not code:
            return False

        secret = self.get_two_factor_secret()
        if verify_totp(secret, code):
            return True

        if self.two_factor_backup_codes:
            hashed_input = hash_backup_code(code.upper().replace(' ', ''))
            try:
                backup_codes = json.loads(self.two_factor_backup_codes)
            except (TypeError, ValueError):
                backup_codes = []

            if hashed_input in backup_codes:
                backup_codes.remove(hashed_input)
                self.two_factor_backup_codes = json.dumps(backup_codes)
                self.save(update_fields=['two_factor_backup_codes'])
                return True
        return False

    def confirm_two_factor(self, code):
        """Confirme le premier TOTP et active la double authentification."""
        from .two_factor import verify_totp

        secret = self.get_two_factor_secret()
        if secret and verify_totp(secret, code):
            self.two_factor_enabled = True
            self.two_factor_confirmed = True
            self.save(update_fields=['two_factor_enabled', 'two_factor_confirmed'])
            return True
        return False

    def disable_two_factor(self):
        self.two_factor_enabled = False
        self.two_factor_secret = ''
        self.two_factor_backup_codes = ''
        self.two_factor_confirmed = False
        self.save(
            update_fields=[
                'two_factor_enabled',
                'two_factor_secret',
                'two_factor_backup_codes',
                'two_factor_confirmed',
            ]
        )

    def is_locked(self):
        return bool(self.locked_until and timezone.now() < self.locked_until)

    def reset_failed_attempts(self):
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=['failed_login_attempts', 'locked_until'])

    def record_failed_attempt(self, lockout_minutes=15, max_attempts=5):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=lockout_minutes)
        self.save(update_fields=['failed_login_attempts', 'locked_until'])


class PasswordChangeToken(models.Model):
    """Token à usage unique pour le changement de mot de passe initial."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_change_tokens',
        verbose_name="Utilisateur",
    )
    token = models.CharField(max_length=64, unique=True, verbose_name="Token")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    used = models.BooleanField(default=False, verbose_name="Utilisé")
    expires_at = models.DateTimeField(verbose_name="Expire le")

    class Meta:
        verbose_name = "Token de changement de mot de passe"
        verbose_name_plural = "Tokens de changement de mot de passe"
        ordering = ['-created_at']

    def __str__(self):
        return f"Token pour {self.user} - {'Utilisé' if self.used else 'Actif'}"

    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at

    def mark_as_used(self):
        self.used = True
        self.save(update_fields=['used'])

    @classmethod
    def generate_token(cls):
        return secrets.token_urlsafe(48)
