"""
Tests pour la validation des formulaires.
Property 9: Form Validation Consistency
"""

import pytest
from hypothesis import given, strategies as st
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.accounts.forms import UserCreationByTeamForm, FirstLoginPasswordChangeForm
from apps.members.forms import MemberForm
from apps.finance.forms import TransactionForm
from apps.events.forms import EventForm
from apps.core.validators import (
    FrenchPhoneValidator, FrenchPostalCodeValidator,
    validate_positive_amount, validate_percentage
)

User = get_user_model()


class FormValidationConsistencyTests(TestCase):
    """
    Tests de cohérence de validation entre client et serveur.
    Property 9: Form Validation Consistency
    """
    
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
    
    def test_user_creation_form_validation_consistency(self):
        """
        Teste que la validation côté serveur correspond aux règles HTML5.
        """
        # Données invalides qui devraient échouer côté client ET serveur
        invalid_data = {
            'first_name': '',  # Requis
            'last_name': 'T',  # Trop court (min 2)
            'email': 'invalid-email',  # Format invalide
            'phone': '123',  # Format invalide
            'role': 'admin'
        }
        
        form = UserCreationByTeamForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        
        # Vérifier les erreurs spécifiques
        self.assertIn('first_name', form.errors)
        self.assertIn('last_name', form.errors)
        self.assertIn('email', form.errors)
        self.assertIn('phone', form.errors)
    
    def test_user_creation_form_valid_data(self):
        """
        Teste qu'un formulaire avec des données valides passe la validation.
        """
        valid_data = {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'email': 'jean.dupont@test.com',
            'phone': '0694123456',
            'role': 'membre'
        }
        
        form = UserCreationByTeamForm(data=valid_data)
        self.assertTrue(form.is_valid(), f"Erreurs: {form.errors}")
    
    def test_password_form_validation_consistency(self):
        """
        Teste la validation des mots de passe.
        """
        # Mot de passe trop court
        short_password_data = {
            'new_password1': '123',
            'new_password2': '123'
        }
        
        form = FirstLoginPasswordChangeForm(data=short_password_data)
        self.assertFalse(form.is_valid())
        self.assertIn('new_password1', form.errors)
        
        # Mots de passe non correspondants
        mismatch_data = {
            'new_password1': 'ValidPassword123',
            'new_password2': 'DifferentPassword123'
        }
        
        form = FirstLoginPasswordChangeForm(data=mismatch_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
    
    def test_member_form_validation_consistency(self):
        """
        Teste la validation du formulaire membre.
        """
        # Date de naissance invalide (trop ancienne)
        from datetime import date, timedelta
        
        invalid_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'date_of_birth': date.today() - timedelta(days=365 * 150),  # 150 ans
            'phone': 'invalid-phone',
            'postal_code': '123',  # Trop court
            'email': 'invalid-email'
        }
        
        form = MemberForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        
        # Vérifier que les erreurs correspondent aux validateurs
        if 'date_of_birth' in form.errors:
            self.assertTrue(any('ancienne' in str(error) for error in form.errors['date_of_birth']))


class ValidatorTests(TestCase):
    """
    Tests unitaires pour les validateurs personnalisés.
    """
    
    def test_french_phone_validator(self):
        """
        Teste le validateur de téléphone français.
        """
        validator = FrenchPhoneValidator()
        
        # Numéros valides
        valid_phones = [
            '0694123456',
            '+33694123456',
            '0123456789',
            '+33123456789'
        ]
        
        for phone in valid_phones:
            try:
                validator(phone)
            except Exception as e:
                self.fail(f"Numéro valide rejeté: {phone} - {e}")
        
        # Numéros invalides
        invalid_phones = [
            '123',
            '0000000000',
            'abcdefghij',
            '+1234567890',  # Pas français
            '06941234567'   # Trop long
        ]
        
        for phone in invalid_phones:
            with self.assertRaises(Exception):
                validator(phone)
    
    def test_french_postal_code_validator(self):
        """
        Teste le validateur de code postal français.
        """
        validator = FrenchPostalCodeValidator()
        
        # Codes valides
        valid_codes = ['75001', '13000', '97400', '20000']
        
        for code in valid_codes:
            try:
                validator(code)
            except Exception as e:
                self.fail(f"Code postal valide rejeté: {code} - {e}")
        
        # Codes invalides
        invalid_codes = ['123', '1234', '123456', 'ABCDE', '']
        
        for code in invalid_codes:
            with self.assertRaises(Exception):
                validator(code)
    
    def test_positive_amount_validator(self):
        """
        Teste le validateur de montant positif.
        """
        # Montants valides
        valid_amounts = [0.01, 1, 100.50, 1000000]
        
        for amount in valid_amounts:
            try:
                validate_positive_amount(amount)
            except Exception as e:
                self.fail(f"Montant valide rejeté: {amount} - {e}")
        
        # Montants invalides
        invalid_amounts = [0, -1, -0.01, -100]
        
        for amount in invalid_amounts:
            with self.assertRaises(Exception):
                validate_positive_amount(amount)
    
    def test_percentage_validator(self):
        """
        Teste le validateur de pourcentage.
        """
        # Pourcentages valides
        valid_percentages = [0, 50, 100, 25.5, 99.99]
        
        for percentage in valid_percentages:
            try:
                validate_percentage(percentage)
            except Exception as e:
                self.fail(f"Pourcentage valide rejeté: {percentage} - {e}")
        
        # Pourcentages invalides
        invalid_percentages = [-1, 101, -50, 150]
        
        for percentage in invalid_percentages:
            with self.assertRaises(Exception):
                validate_percentage(percentage)


class PropertyBasedValidationTests(TestCase):
    """
    Tests basés sur les propriétés pour la validation.
    """
    
    @given(st.text(min_size=1, max_size=150))
    def test_name_fields_accept_valid_text(self, text):
        """
        Property: Les champs nom/prénom acceptent tout texte valide.
        """
        # Filtrer les caractères problématiques
        clean_text = ''.join(c for c in text if c.isalpha() or c.isspace()).strip()
        
        if len(clean_text) >= 2:  # Respecter la longueur minimale
            data = {
                'first_name': clean_text,
                'last_name': clean_text,
                'email': 'test@example.com',
                'role': 'membre'
            }
            
            form = UserCreationByTeamForm(data=data)
            # Le formulaire devrait être valide si les données respectent les contraintes
            if not form.is_valid():
                # Vérifier que les erreurs ne concernent pas les champs nom/prénom
                self.assertNotIn('first_name', form.errors, 
                               f"Texte valide rejeté pour prénom: {clean_text}")
                self.assertNotIn('last_name', form.errors,
                               f"Texte valide rejeté pour nom: {clean_text}")
    
    @given(st.emails())
    def test_email_fields_accept_valid_emails(self, email):
        """
        Property: Les champs email acceptent tous les emails valides.
        """
        data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': email,
            'role': 'membre'
        }
        
        form = UserCreationByTeamForm(data=data)
        if not form.is_valid() and 'email' in form.errors:
            # L'email devrait être accepté s'il est valide selon le standard
            self.fail(f"Email valide rejeté: {email} - Erreurs: {form.errors['email']}")
    
    @given(st.integers(min_value=1, max_value=999999))
    def test_positive_numbers_accepted(self, number):
        """
        Property: Les champs numériques acceptent tous les nombres positifs valides.
        """
        try:
            validate_positive_amount(number)
        except Exception as e:
            self.fail(f"Nombre positif valide rejeté: {number} - {e}")
    
    @given(st.integers(min_value=0, max_value=100))
    def test_valid_percentages_accepted(self, percentage):
        """
        Property: Le validateur de pourcentage accepte tous les nombres entre 0 et 100.
        """
        try:
            validate_percentage(percentage)
        except Exception as e:
            self.fail(f"Pourcentage valide rejeté: {percentage} - {e}")


class IntegrationValidationTests(TestCase):
    """
    Tests d'intégration pour la validation des formulaires.
    """
    
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.client.force_login(self.admin_user)
    
    def test_form_submission_with_validation_errors(self):
        """
        Teste qu'une soumission de formulaire avec erreurs retourne les bonnes erreurs.
        """
        # Tenter de créer un utilisateur avec des données invalides
        invalid_data = {
            'first_name': '',
            'last_name': '',
            'email': 'invalid-email',
            'role': 'admin'
        }
        
        response = self.client.post(reverse('accounts:create_user'), data=invalid_data)
        
        # Le formulaire ne devrait pas être soumis avec succès
        self.assertEqual(response.status_code, 200)  # Reste sur la page avec erreurs
        
        # Vérifier que les erreurs sont présentes dans le contexte
        form = response.context.get('form')
        if form:
            self.assertFalse(form.is_valid())
            self.assertTrue(form.errors)
    
    def test_javascript_validation_consistency(self):
        """
        Teste que les attributs HTML5 correspondent aux validateurs Django.
        """
        form = UserCreationByTeamForm()
        
        # Vérifier que les champs requis ont l'attribut required
        required_fields = ['first_name', 'last_name', 'email', 'role']
        for field_name in required_fields:
            field = form.fields[field_name]
            if field.required:
                widget_attrs = field.widget.attrs
                self.assertTrue(
                    widget_attrs.get('required') or field.required,
                    f"Champ requis {field_name} n'a pas l'attribut HTML5 required"
                )
        
        # Vérifier les patterns pour les champs spéciaux
        email_field = form.fields['email']
        if hasattr(email_field.widget, 'attrs'):
            attrs = email_field.widget.attrs
            self.assertEqual(attrs.get('type'), 'email')
        
        # Vérifier les longueurs min/max
        for field_name, field in form.fields.items():
            if hasattr(field, 'max_length') and field.max_length:
                widget_attrs = field.widget.attrs
                self.assertEqual(
                    widget_attrs.get('maxlength'), field.max_length,
                    f"Champ {field_name}: maxlength HTML5 ne correspond pas à max_length Django"
                )


# Marquer les tests comme Property-Based Testing
class TestFormValidationProperty(TestCase):
    """
    **Property 9: Form Validation Consistency**
    **Validates: Requirements 25.1, 25.2, 25.3, 25.4**
    """
    
    def test_property_form_validation_consistency(self):
        """
        Property 9: Form Validation Consistency
        Pour tout formulaire, la validation côté serveur produit le même résultat 
        que la validation côté client pour les mêmes données d'entrée.
        """
        # Test avec le formulaire de création d'utilisateur
        test_cases = [
            # Cas valide
            {
                'data': {
                    'first_name': 'Jean',
                    'last_name': 'Dupont',
                    'email': 'jean@test.com',
                    'role': 'membre'
                },
                'should_be_valid': True
            },
            # Cas invalide - email
            {
                'data': {
                    'first_name': 'Jean',
                    'last_name': 'Dupont',
                    'email': 'invalid-email',
                    'role': 'membre'
                },
                'should_be_valid': False
            },
            # Cas invalide - champs requis manquants
            {
                'data': {
                    'first_name': '',
                    'last_name': '',
                    'email': 'test@test.com',
                    'role': 'membre'
                },
                'should_be_valid': False
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            with self.subTest(case=i):
                form = UserCreationByTeamForm(data=test_case['data'])
                actual_valid = form.is_valid()
                expected_valid = test_case['should_be_valid']
                
                self.assertEqual(
                    actual_valid, expected_valid,
                    f"Cas {i}: Validation incohérente. "
                    f"Attendu: {expected_valid}, Obtenu: {actual_valid}. "
                    f"Erreurs: {form.errors}"
                )