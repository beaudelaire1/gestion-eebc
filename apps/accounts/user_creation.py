"""
Service de création d'utilisateurs par l'équipe.
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
    """
    import unicodedata
    
    # Nettoyer et normaliser les noms
    first_clean = unicodedata.normalize('NFD', first_name.lower())
    first_clean = ''.join(c for c in first_clean if unicodedata.category(c) != 'Mn')
    
    last_clean = unicodedata.normalize('NFD', last_name.lower())
    last_clean = ''.join(c for c in last_clean if unicodedata.category(c) != 'Mn')
    
    # Prendre les 2 premières lettres du prénom + nom complet
    first_part = first_clean[:2] if len(first_clean) >= 2 else first_clean
    username = f"{first_part}_{last_clean}"
    
    # Vérifier l'unicité et ajouter un numéro si nécessaire
    original_username = username
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{original_username}{counter}"
        counter += 1
    
    return username


def generate_password(length=12):
    """
    Génère un mot de passe sécurisé.
    """
    # Caractères autorisés (éviter les caractères ambigus)
    chars = string.ascii_letters + string.digits + "!@#$%&*"
    chars = chars.replace('0', '').replace('O', '').replace('l', '').replace('I', '')
    
    password = ''.join(secrets.choice(chars) for _ in range(length))
    
    # S'assurer qu'il y a au moins une majuscule, une minuscule, un chiffre et un symbole
    if not any(c.isupper() for c in password):
        password = password[:-1] + secrets.choice(string.ascii_uppercase)
    if not any(c.islower() for c in password):
        password = password[:-1] + secrets.choice(string.ascii_lowercase)
    if not any(c.isdigit() for c in password):
        password = password[:-1] + secrets.choice(string.digits)
    if not any(c in "!@#$%&*" for c in password):
        password = password[:-1] + secrets.choice("!@#$%&*")
    
    return password


def create_user_by_team(first_name, last_name, email, role, created_by, phone=''):
    """
    Crée un nouvel utilisateur avec identifiants générés automatiquement.
    
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
    try:
        # Générer les identifiants
        username = generate_username(first_name, last_name)
        password = generate_password()
        
        # Créer l'utilisateur
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            role=role,
            phone=phone,
            created_by_team=True,
            created_by=created_by,
            must_change_password=True  # Forcer le changement de mot de passe
        )
        
        # Le mot de passe est utilisable mais l'utilisateur doit le changer
        # On ne rend plus le mot de passe inutilisable
        
        # Envoyer l'email d'invitation
        send_invitation_email(user, username, password, created_by)
        
        return user, username, password
        
    except Exception as e:
        print(f"Erreur lors de la création de l'utilisateur: {e}")
        return None, None, None


def send_invitation_email(user, username, password, created_by):
    """
    Envoie l'email d'invitation avec les identifiants.
    """
    try:
        context = {
            'user': user,
            'username': username,
            'password': password,
            'created_by': created_by,
            'login_url': f"{settings.SITE_URL}/accounts/login/",
            'site_name': getattr(settings, 'SITE_NAME', 'EEBC'),
        }
        
        # Rendu du template email
        html_message = render_to_string('accounts/emails/user_invitation.html', context)
        plain_message = strip_tags(html_message)
        
        # Envoi de l'email
        send_mail(
            subject=f"Invitation à rejoindre {context['site_name']}",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return True
        
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email d'invitation: {e}")
        return False


def send_password_reset_email(user, username, password, reset_by):
    """
    Envoie l'email de réinitialisation de mot de passe.
    """
    try:
        context = {
            'user': user,
            'username': username,
            'password': password,
            'reset_by': reset_by,
            'login_url': f"{settings.SITE_URL}/accounts/login/",
            'site_name': getattr(settings, 'SITE_NAME', 'EEBC'),
        }
        
        # Rendu du template email
        html_message = render_to_string('accounts/emails/password_reset.html', context)
        plain_message = strip_tags(html_message)
        
        # Envoi de l'email
        send_mail(
            subject=f"Réinitialisation de votre mot de passe - {context['site_name']}",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return True
        
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email de réinitialisation: {e}")
        return False


def activate_user_account(user, new_password):
    """
    Active le compte utilisateur après le premier changement de mot de passe.
    """
    try:
        user.set_password(new_password)
        user.save()
        return True
    except Exception as e:
        print(f"Erreur lors de l'activation du compte: {e}")
        return False