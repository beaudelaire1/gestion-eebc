"""
Formulaires de base et mixins pour la validation HTML5.
"""

from django import forms
from django.core.exceptions import ValidationError
import re


class HTML5ValidationMixin:
    """
    Mixin pour ajouter automatiquement les attributs de validation HTML5.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_html5_validation()
    
    def add_html5_validation(self):
        """Ajoute les attributs HTML5 de validation aux champs."""
        for field_name, field in self.fields.items():
            widget = field.widget
            
            # Ajouter 'required' pour les champs obligatoires
            if field.required and not isinstance(widget, forms.CheckboxInput):
                widget.attrs['required'] = True
            
            # Validation spécifique par type de champ
            if isinstance(field, forms.EmailField):
                widget.attrs['type'] = 'email'
                widget.attrs['pattern'] = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                widget.attrs['title'] = 'Veuillez saisir une adresse email valide'
            
            elif isinstance(field, forms.URLField):
                widget.attrs['type'] = 'url'
                widget.attrs['title'] = 'Veuillez saisir une URL valide (ex: https://exemple.com)'
            
            elif isinstance(field, forms.CharField):
                # Ajouter maxlength
                if hasattr(field, 'max_length') and field.max_length:
                    widget.attrs['maxlength'] = field.max_length
                
                # Ajouter minlength si défini
                if hasattr(field, 'min_length') and field.min_length:
                    widget.attrs['minlength'] = field.min_length
                
                # Patterns spécifiques pour certains champs
                if 'phone' in field_name.lower() or 'telephone' in field_name.lower():
                    widget.attrs['type'] = 'tel'
                    widget.attrs['pattern'] = r'[0-9\s\-\+\(\)]{10,}'
                    widget.attrs['title'] = 'Numéro de téléphone (ex: 0694 12 34 56)'
                
                elif 'postal' in field_name.lower() or 'zip' in field_name.lower():
                    widget.attrs['pattern'] = r'[0-9]{5}'
                    widget.attrs['title'] = 'Code postal (5 chiffres)'
                    widget.attrs['maxlength'] = 5
            
            elif isinstance(field, forms.IntegerField):
                widget.attrs['type'] = 'number'
                if hasattr(field, 'min_value') and field.min_value is not None:
                    widget.attrs['min'] = field.min_value
                if hasattr(field, 'max_value') and field.max_value is not None:
                    widget.attrs['max'] = field.max_value
            
            elif isinstance(field, forms.DecimalField) or isinstance(field, forms.FloatField):
                widget.attrs['type'] = 'number'
                if hasattr(field, 'min_value') and field.min_value is not None:
                    widget.attrs['min'] = field.min_value
                if hasattr(field, 'max_value') and field.max_value is not None:
                    widget.attrs['max'] = field.max_value
                
                # Ajouter step pour les décimaux
                if isinstance(field, forms.DecimalField):
                    if hasattr(field, 'decimal_places') and field.decimal_places:
                        widget.attrs['step'] = '0.' + '0' * (field.decimal_places - 1) + '1'
                    else:
                        widget.attrs['step'] = '0.01'
            
            elif isinstance(field, forms.DateField):
                widget.attrs['type'] = 'date'
            
            elif isinstance(field, forms.TimeField):
                widget.attrs['type'] = 'time'
            
            elif isinstance(field, forms.DateTimeField):
                widget.attrs['type'] = 'datetime-local'
            
            # Ajouter des classes CSS si pas déjà présentes
            css_classes = widget.attrs.get('class', '')
            if isinstance(widget, (forms.TextInput, forms.EmailInput, forms.NumberInput, 
                                 forms.DateInput, forms.TimeInput, forms.Textarea)):
                if 'form-control' not in css_classes:
                    widget.attrs['class'] = f"{css_classes} form-control".strip()
            elif isinstance(widget, forms.Select):
                if 'form-select' not in css_classes:
                    widget.attrs['class'] = f"{css_classes} form-select".strip()
            elif isinstance(widget, forms.CheckboxInput):
                if 'form-check-input' not in css_classes:
                    widget.attrs['class'] = f"{css_classes} form-check-input".strip()


class BaseForm(HTML5ValidationMixin, forms.Form):
    """Formulaire de base avec validation HTML5."""
    pass


class BaseModelForm(HTML5ValidationMixin, forms.ModelForm):
    """Formulaire modèle de base avec validation HTML5."""
    pass


class FrenchErrorMessagesMixin:
    """
    Mixin pour traduire les messages d'erreur en français.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.customize_error_messages()
    
    def customize_error_messages(self):
        """Personnalise les messages d'erreur en français."""
        french_messages = {
            'required': 'Ce champ est obligatoire.',
            'invalid': 'Veuillez saisir une valeur valide.',
            'invalid_email': 'Veuillez saisir une adresse email valide (ex: nom@exemple.com).',
            'invalid_url': 'Veuillez saisir une URL valide (ex: https://exemple.com).',
            'invalid_date': 'Veuillez saisir une date valide au format JJ/MM/AAAA.',
            'invalid_time': 'Veuillez saisir une heure valide au format HH:MM.',
            'invalid_datetime': 'Veuillez saisir une date et heure valides.',
            'invalid_number': 'Veuillez saisir un nombre valide.',
            'invalid_integer': 'Veuillez saisir un nombre entier.',
            'invalid_decimal': 'Veuillez saisir un nombre décimal valide.',
            'min_value': 'Cette valeur doit être supérieure ou égale à %(limit_value)s.',
            'max_value': 'Cette valeur doit être inférieure ou égale à %(limit_value)s.',
            'min_length': 'Ce champ doit contenir au moins %(limit_value)d caractères.',
            'max_length': 'Ce champ ne peut pas contenir plus de %(limit_value)d caractères.',
            'unique': 'Cette valeur existe déjà. Veuillez en choisir une autre.',
            'unique_together': 'Cette combinaison de valeurs existe déjà.',
            'blank': 'Ce champ ne peut pas être vide.',
            'null': 'Ce champ ne peut pas être nul.',
            'invalid_choice': 'Sélectionnez un choix valide. %(value)s n\'est pas un des choix disponibles.',
            'empty': 'Ce champ ne peut pas être vide.',
            'missing': 'Ce champ est manquant.',
            'invalid_image': 'Veuillez télécharger une image valide. Le fichier que vous avez téléchargé n\'est pas une image ou est corrompu.',
            'invalid_extension': 'L\'extension de fichier "%(extension)s" n\'est pas autorisée. Les extensions autorisées sont : %(allowed_extensions)s.',
            'file_size': 'Veuillez vous assurer que ce fichier fait moins de %(max_size)s. Sa taille actuelle est de %(size)s.',
            'password_too_short': 'Ce mot de passe est trop court. Il doit contenir au moins %(min_length)d caractères.',
            'password_too_common': 'Ce mot de passe est trop commun.',
            'password_entirely_numeric': 'Ce mot de passe ne peut pas être entièrement numérique.',
            'password_mismatch': 'Les deux mots de passe ne correspondent pas.',
        }
        
        # Messages spécifiques par type de champ
        field_specific_messages = {
            'email': {
                'invalid': 'Veuillez saisir une adresse email valide (ex: nom@exemple.com).',
            },
            'phone': {
                'invalid': 'Veuillez saisir un numéro de téléphone valide (ex: 0694123456).',
            },
            'postal_code': {
                'invalid': 'Veuillez saisir un code postal valide (5 chiffres).',
            },
            'url': {
                'invalid': 'Veuillez saisir une URL valide commençant par http:// ou https://.',
            },
            'date_of_birth': {
                'invalid': 'Veuillez saisir une date de naissance valide.',
            },
            'amount': {
                'invalid': 'Veuillez saisir un montant valide (ex: 25.50).',
                'min_value': 'Le montant doit être positif.',
            },
            'percentage': {
                'min_value': 'Le pourcentage doit être entre 0 et 100.',
                'max_value': 'Le pourcentage doit être entre 0 et 100.',
            }
        }
        
        for field_name, field in self.fields.items():
            if hasattr(field, 'error_messages'):
                # Appliquer les messages généraux
                field.error_messages.update(french_messages)
                
                # Appliquer les messages spécifiques au champ
                for pattern, messages in field_specific_messages.items():
                    if pattern in field_name.lower():
                        field.error_messages.update(messages)
                        break
                
                # Messages spécifiques par type de widget
                if isinstance(field.widget, forms.EmailInput):
                    field.error_messages.update(field_specific_messages['email'])
                elif isinstance(field.widget, forms.URLInput):
                    field.error_messages.update(field_specific_messages['url'])
                elif isinstance(field.widget, forms.NumberInput):
                    if 'amount' in field_name.lower() or 'price' in field_name.lower():
                        field.error_messages.update(field_specific_messages['amount'])
    
    def add_error(self, field, error):
        """Surcharge pour personnaliser l'ajout d'erreurs."""
        if field is None:
            # Erreur non liée à un champ spécifique
            super().add_error(field, error)
        else:
            # Personnaliser le message selon le contexte
            if isinstance(error, str):
                error = self.customize_error_message(field, error)
            super().add_error(field, error)
    
    def customize_error_message(self, field_name, message):
        """Personnalise un message d'erreur selon le contexte."""
        # Ajouter du contexte aux messages génériques
        if message == "Ce champ est obligatoire.":
            field_label = self.fields[field_name].label or field_name
            return f"Le champ '{field_label}' est obligatoire."
        
        return message


class EnhancedForm(FrenchErrorMessagesMixin, HTML5ValidationMixin, forms.Form):
    """Formulaire complet avec validation HTML5 et messages français."""
    pass


class EnhancedModelForm(FrenchErrorMessagesMixin, HTML5ValidationMixin, forms.ModelForm):
    """Formulaire modèle complet avec validation HTML5 et messages français."""
    pass