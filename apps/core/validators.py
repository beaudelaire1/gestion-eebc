"""
Validators personnalisés pour la validation des données.
"""
import re
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


# Validator pour les numéros de téléphone français/Guyane
phone_validator = RegexValidator(
    regex=r'^\+?(?:33|594)?[0-9]{9,10}$',
    message=_("Format de téléphone invalide. Utilisez le format : 0694123456 ou +594694123456")
)

# Validator pour les emails avec domaines autorisés
def validate_email_domain(value):
    """
    Valide que l'email provient d'un domaine autorisé.
    Peut être configuré via les settings.
    """
    from django.conf import settings
    
    allowed_domains = getattr(settings, 'ALLOWED_EMAIL_DOMAINS', None)
    if allowed_domains:
        domain = value.split('@')[1].lower()
        if domain not in allowed_domains:
            raise ValidationError(
                _("Le domaine email '%(domain)s' n'est pas autorisé."),
                params={'domain': domain}
            )

# Validator pour les mots de passe forts
def validate_strong_password(password):
    """
    Valide qu'un mot de passe respecte les critères de sécurité.
    """
    if len(password) < 12:
        raise ValidationError(_("Le mot de passe doit contenir au moins 12 caractères."))
    
    if not re.search(r'[A-Z]', password):
        raise ValidationError(_("Le mot de passe doit contenir au moins une majuscule."))
    
    if not re.search(r'[a-z]', password):
        raise ValidationError(_("Le mot de passe doit contenir au moins une minuscule."))
    
    if not re.search(r'[0-9]', password):
        raise ValidationError(_("Le mot de passe doit contenir au moins un chiffre."))
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError(_("Le mot de passe doit contenir au moins un caractère spécial."))

# Validator pour les codes postaux français/Guyane
postal_code_validator = RegexValidator(
    regex=r'^(?:97[3-6]|0[1-9]|[1-8][0-9]|9[0-5])[0-9]{2}$',
    message=_("Code postal invalide. Format attendu : 97300 (Guyane) ou 75001 (France métropolitaine)")
)

# Validator pour les numéros SIRET/SIREN
siret_validator = RegexValidator(
    regex=r'^[0-9]{14}$',
    message=_("Numéro SIRET invalide. 14 chiffres attendus.")
)

siren_validator = RegexValidator(
    regex=r'^[0-9]{9}$',
    message=_("Numéro SIREN invalide. 9 chiffres attendus.")
)

# Validator pour les montants financiers
def validate_positive_amount(value):
    """Valide qu'un montant est positif."""
    if value <= 0:
        raise ValidationError(_("Le montant doit être positif."))

def validate_reasonable_amount(value):
    """Valide qu'un montant est raisonnable (< 1M€)."""
    if value > 1000000:
        raise ValidationError(_("Le montant semble trop élevé. Vérifiez la saisie."))

# Validator pour les âges
def validate_age_range(value):
    """Valide qu'un âge est dans une plage raisonnable."""
    if value < 0 or value > 120:
        raise ValidationError(_("L'âge doit être compris entre 0 et 120 ans."))

# Validator pour les dates de naissance
def validate_birth_date(value):
    """Valide qu'une date de naissance est cohérente."""
    from datetime import date
    today = date.today()
    
    if value > today:
        raise ValidationError(_("La date de naissance ne peut pas être dans le futur."))
    
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    if age > 120:
        raise ValidationError(_("La date de naissance semble trop ancienne."))

# Validator pour les URLs sécurisées
def validate_secure_url(value):
    """Valide qu'une URL utilise HTTPS."""
    if not value.startswith('https://'):
        raise ValidationError(_("Seules les URLs HTTPS sont autorisées."))

# Validator pour les noms de fichiers sécurisés
def validate_safe_filename(value):
    """Valide qu'un nom de fichier est sécurisé."""
    import os
    
    # Caractères interdits
    forbidden_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
    if any(char in value for char in forbidden_chars):
        raise ValidationError(_("Le nom de fichier contient des caractères interdits."))
    
    # Extensions interdites
    forbidden_extensions = ['.exe', '.bat', '.cmd', '.scr', '.pif', '.com']
    _, ext = os.path.splitext(value.lower())
    if ext in forbidden_extensions:
        raise ValidationError(_("Type de fichier non autorisé."))

# Validator pour les codes couleur hexadécimaux
hex_color_validator = RegexValidator(
    regex=r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
    message=_("Code couleur invalide. Format attendu : #FF0000 ou #F00")
)

# Validator pour les identifiants membres EEBC
member_id_validator = RegexValidator(
    regex=r'^EEBC-(CAB|MAC)-[0-9]{4,6}$',
    message=_("ID membre invalide. Format attendu : EEBC-CAB-1234 ou EEBC-MAC-5678")
)