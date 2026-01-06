"""
Service de création d'utilisateurs par l'équipe.

NOTE: Ce module est conservé pour la rétrocompatibilité.
La logique métier a été déplacée vers apps/accounts/services.py (AccountsService).
Les fonctions ci-dessous délèguent maintenant au service.
"""
import secrets
import string
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags

User = get_user_model()


def generate_username(first_name, last_name):
    """
    Génère un nom d'utilisateur au format: prénom_nom (en minuscules, sans accents).
    Ex: Paul Kapel -> pa_kapel
    
    NOTE: Délègue à AccountsService.generate_username()
    """
    from .services import AccountsService
    return AccountsService.generate_username(first_name, last_name)


def generate_password(length=12):
    """
    Génère un mot de passe sécurisé.
    
    NOTE: Délègue à AccountsService.generate_password()
    """
    from .services import AccountsService
    return AccountsService.generate_password(length)


def create_user_by_team(first_name, last_name, email, role, created_by, phone=''):
    """
    Crée un nouvel utilisateur avec identifiants générés automatiquement.
    
    NOTE: Délègue à AccountsService.create_user_by_team()
    
    Args:
        first_name: Prénom
        last_name: Nom
        email: Email
        role: Rôle (User.Role)
        created_by: Utilisateur qui crée le compte
        phone: Téléphone (optionnel)
    
    Returns:
        tuple: (user, username, password) ou (None, None, None) si erreur
    """
    from .services import AccountsService
    
    result = AccountsService.create_user_by_team(
        first_name=first_name,
        last_name=last_name,
        email=email,
        role=role,
        created_by=created_by,
        phone=phone
    )
    
    if result.success:
        return result.data['user'], result.data['username'], result.data['password']
    else:
        return None, None, None


def send_invitation_email(user, username, password, created_by):
    """
    Envoie l'email d'invitation avec les identifiants.
    
    NOTE: Délègue à AccountsService.send_invitation_email()
    """
    from .services import AccountsService
    return AccountsService.send_invitation_email(user, username, password, created_by)


def send_password_reset_email(user, username, password, reset_by):
    """
    Envoie l'email de réinitialisation de mot de passe.
    
    NOTE: Délègue à AccountsService.send_password_reset_email()
    """
    from .services import AccountsService
    return AccountsService.send_password_reset_email(user, username, password, reset_by)


def activate_user_account(user, new_password):
    """
    Active le compte utilisateur après le premier changement de mot de passe.
    
    NOTE: Délègue à AccountsService.activate_user_account()
    """
    from .services import AccountsService
    result = AccountsService.activate_user_account(user, new_password)
    return result.success