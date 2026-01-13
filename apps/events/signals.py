"""
Signals pour synchroniser les événements internes avec les événements publics.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.text import slugify
from .models import Event


@receiver(post_save, sender=Event)
def sync_public_event(sender, instance, created, **kwargs):
    """
    Synchronise un Event avec PublicEvent quand visibility='public'.
    Crée ou met à jour le PublicEvent correspondant.
    """
    from apps.core.models import PublicEvent
    
    if instance.visibility == 'public':
        # Générer un slug unique
        base_slug = slugify(instance.title)
        slug = base_slug
        counter = 1
        
        # Vérifier si un PublicEvent existe déjà pour cet Event
        existing = PublicEvent.objects.filter(internal_event=instance).first()
        
        if existing:
            # Mettre à jour l'existant
            existing.title = instance.title
            existing.description = instance.description or instance.title
            existing.start_date = instance.start_date
            existing.start_time = instance.start_time
            existing.end_date = instance.end_date
            existing.end_time = instance.end_time
            existing.location = instance.location or ''
            existing.site = instance.site
            existing.is_published = True
            existing.save()
        else:
            # Créer un nouveau PublicEvent
            # S'assurer que le slug est unique
            while PublicEvent.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            PublicEvent.objects.create(
                internal_event=instance,
                title=instance.title,
                slug=slug,
                description=instance.description or instance.title,
                start_date=instance.start_date,
                start_time=instance.start_time,
                end_date=instance.end_date,
                end_time=instance.end_time,
                location=instance.location or '',
                site=instance.site,
                is_published=True,
                allow_registration=False,
            )
    else:
        # Si l'événement n'est plus public, dépublier le PublicEvent
        from apps.core.models import PublicEvent
        PublicEvent.objects.filter(internal_event=instance).update(is_published=False)


@receiver(post_delete, sender=Event)
def delete_public_event(sender, instance, **kwargs):
    """
    Supprime le PublicEvent quand l'Event interne est supprimé.
    """
    from apps.core.models import PublicEvent
    PublicEvent.objects.filter(internal_event=instance).delete()
