"""
Validateurs personnalisés avec messages d'erreur en français.
"""

import re
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


class FrenchPhoneValidator(RegexValidator):
    """Validateur pour les numéros de téléphone français."""
    
    regex = r'^(?:(?:\+33|0)[1-9](?:[0-9]{8}))$'
    message = 'Veuillez saisir un numéro de téléphone français valide (ex: 0694123456 ou +33694123456).'
    
    def __call__(self, value):
        # Nettoyer le numéro (supprimer espaces, tirets, etc.)
        cleaned_value = re.sub(r'[\s\-\(\)\.]+', '', str(value))
        super().__call__(cleaned_value)


class FrenchPostalCodeValidator(RegexValidator):
    """Validateur pour les codes postaux français."""
    
    regex = r'^[0-9]{5}$'
    message = 'Veuillez saisir un code postal français valide (5 chiffres).'


class PasswordStrengthValidator:
    """Validateur de force de mot de passe."""
    
    def __init__(self, min_length=8):
        self.min_length = min_length
    
    def validate(self, password, user=None):
        errors = []
        
        if len(password) < self.min_length:
            errors.append(f'Le mot de passe doit contenir au moins {self.min_length} caractères.')
        
        if not re.search(r'[A-Z]', password):
            errors.append('Le mot de passe doit contenir au moins une majuscule.')
        
        if not re.search(r'[a-z]', password):
            errors.append('Le mot de passe doit contenir au moins une minuscule.')
        
        if not re.search(r'\d', password):
            errors.append('Le mot de passe doit contenir au moins un chiffre.')
        
        if errors:
            raise ValidationError(errors)
    
    def get_help_text(self):
        return f'Votre mot de passe doit contenir au moins {self.min_length} caractères, une majuscule, une minuscule et un chiffre.'


class FileExtensionValidator:
    """Validateur d'extension de fichier avec messages français."""
    
    def __init__(self, allowed_extensions):
        self.allowed_extensions = [ext.lower() for ext in allowed_extensions]
    
    def __call__(self, value):
        if hasattr(value, 'name'):
            filename = value.name
            extension = filename.split('.')[-1].lower() if '.' in filename else ''
            
            if extension not in self.allowed_extensions:
                raise ValidationError(
                    f'Extension de fichier non autorisée. '
                    f'Extensions autorisées : {", ".join(self.allowed_extensions)}'
                )


class FileSizeValidator:
    """Validateur de taille de fichier avec messages français."""
    
    def __init__(self, max_size_mb):
        self.max_size_mb = max_size_mb
        self.max_size_bytes = max_size_mb * 1024 * 1024
    
    def __call__(self, value):
        if hasattr(value, 'size') and value.size > self.max_size_bytes:
            raise ValidationError(
                f'Le fichier est trop volumineux. '
                f'Taille maximale autorisée : {self.max_size_mb} MB. '
                f'Taille actuelle : {value.size / (1024 * 1024):.1f} MB.'
            )


def validate_future_date(value):
    """Valide qu'une date est dans le futur."""
    from datetime import date
    if value <= date.today():
        raise ValidationError('Cette date doit être dans le futur.')


def validate_past_date(value):
    """Valide qu'une date est dans le passé."""
    from datetime import date
    if value >= date.today():
        raise ValidationError('Cette date doit être dans le passé.')


def validate_reasonable_birth_date(value):
    """Valide qu'une date de naissance est raisonnable."""
    from datetime import date, timedelta
    
    today = date.today()
    min_date = today - timedelta(days=365 * 120)  # 120 ans max
    max_date = today - timedelta(days=365 * 5)    # 5 ans min
    
    if value < min_date:
        raise ValidationError('Cette date de naissance semble trop ancienne.')
    
    if value > max_date:
        raise ValidationError('Cette date de naissance semble trop récente.')


def validate_positive_amount(value):
    """Valide qu'un montant est positif."""
    if value <= 0:
        raise ValidationError('Le montant doit être positif.')


def validate_percentage(value):
    """Valide qu'une valeur est un pourcentage valide (0-100)."""
    if not (0 <= value <= 100):
        raise ValidationError('La valeur doit être comprise entre 0 et 100.')


def validate_no_special_chars(value):
    """Valide qu'une chaîne ne contient pas de caractères spéciaux dangereux."""
    dangerous_chars = ['<', '>', '"', "'", '&', 'script', 'javascript']
    value_lower = value.lower()
    
    for char in dangerous_chars:
        if char in value_lower:
            raise ValidationError('Ce champ ne peut pas contenir de caractères spéciaux dangereux.')


# Validateurs prêts à l'emploi
phone_validator = FrenchPhoneValidator()
postal_code_validator = FrenchPostalCodeValidator()
image_validator = FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif', 'webp'])
document_validator = FileExtensionValidator(['pdf', 'doc', 'docx', 'txt'])
small_image_validator = FileSizeValidator(5)  # 5 MB max
large_file_validator = FileSizeValidator(50)  # 50 MB max