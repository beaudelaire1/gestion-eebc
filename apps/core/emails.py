"""
Service d'envoi d'emails pour le site vitrine.
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags


def send_contact_notification(contact_message):
    """
    Envoie une notification email quand un message de contact est reçu.
    
    - Email à l'équipe de l'église
    - Email de confirmation au visiteur
    """
    from .models import SiteSettings
    
    site_settings = SiteSettings.get_settings()
    site_name = site_settings.site_name or 'EEBC'
    admin_email = site_settings.email or settings.DEFAULT_FROM_EMAIL
    
    # 1. Email à l'équipe de l'église
    subject_admin = f"[{site_name}] Nouveau message de contact - {contact_message.get_subject_display()}"
    
    html_content_admin = render_to_string('emails/contact_notification_admin.html', {
        'contact': contact_message,
        'site_name': site_name,
    })
    text_content_admin = strip_tags(html_content_admin)
    
    try:
        send_mail(
            subject=subject_admin,
            message=text_content_admin,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_email],
            html_message=html_content_admin,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Erreur envoi email admin: {e}")
    
    # 2. Email de confirmation au visiteur
    subject_visitor = f"Merci pour votre message - {site_name}"
    
    html_content_visitor = render_to_string('emails/contact_confirmation.html', {
        'contact': contact_message,
        'site_name': site_name,
    })
    text_content_visitor = strip_tags(html_content_visitor)
    
    try:
        send_mail(
            subject=subject_visitor,
            message=text_content_visitor,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[contact_message.email],
            html_message=html_content_visitor,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Erreur envoi email visiteur: {e}")


def send_registration_notification(registration):
    """
    Envoie une notification email quand un visiteur s'inscrit.
    
    - Email à l'équipe de l'église
    - Email de confirmation au visiteur
    """
    from .models import SiteSettings
    
    site_settings = SiteSettings.get_settings()
    site_name = site_settings.site_name or 'EEBC'
    admin_email = site_settings.email or settings.DEFAULT_FROM_EMAIL
    
    # 1. Email à l'équipe de l'église
    subject_admin = f"[{site_name}] Nouvelle inscription - {registration.first_name} {registration.last_name}"
    
    html_content_admin = render_to_string('emails/registration_notification_admin.html', {
        'registration': registration,
        'site_name': site_name,
    })
    text_content_admin = strip_tags(html_content_admin)
    
    try:
        send_mail(
            subject=subject_admin,
            message=text_content_admin,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_email],
            html_message=html_content_admin,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Erreur envoi email admin: {e}")
    
    # 2. Email de confirmation au visiteur
    subject_visitor = f"Bienvenue ! - {site_name}"
    
    html_content_visitor = render_to_string('emails/registration_confirmation.html', {
        'registration': registration,
        'site_name': site_name,
        'site_settings': site_settings,
    })
    text_content_visitor = strip_tags(html_content_visitor)
    
    try:
        send_mail(
            subject=subject_visitor,
            message=text_content_visitor,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[registration.email],
            html_message=html_content_visitor,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Erreur envoi email visiteur: {e}")
