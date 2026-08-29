"""
Centre de Notifications - Signaux automatiques.

Ce module centralise toutes les règles d'automatisation pour les notifications :
- Règle 1 : Notification des assignations de rôles (WorshipService)
- Règle 2 : Annonce des naissances le dimanche (LifeEvent)
- Règle 3 : Rappel des membres non visités (Celery task)
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='members.LifeEvent')
def handle_life_event_notification(sender, instance, created, **kwargs):
    """
    Gère les notifications liées aux événements de vie.
    
    Règle 2 : Si LifeEvent type "Naissance" -> Créer une Notification 
    "Annoncer ce dimanche" pour le pasteur.
    """
    if not created:
        return
    
    from apps.communication.models import Notification
    from apps.accounts.models import User
    from apps.members.models import VisitationLog
    
    # Notifier les pasteurs/admins
    pastors = User.objects.filter(role__icontains='pasteur', is_active=True) | User.objects.filter(role__icontains='admin', is_active=True)
    
    # Notifications selon le type d'événement
    if instance.event_type == 'naissance':
        for pastor in pastors:
            Notification.objects.create(
                user=pastor,
                title=f"🎉 Naissance à annoncer : {instance.title}",
                message=f"Une naissance a été enregistrée pour {instance.primary_member.full_name}. "
                        f"Pensez à l'annoncer lors du prochain culte.",
                notification_type='info',
                action_url=f"/admin/members/lifeevent/{instance.pk}/change/"
            )
    
    elif instance.event_type == 'deces':
        for pastor in pastors:
            Notification.objects.create(
                user=pastor,
                title=f"⚫ Décès : {instance.title}",
                message=f"Un décès a été enregistré concernant {instance.primary_member.full_name}. "
                        f"Une visite pastorale est recommandée.",
                notification_type='warning',
                action_url=f"/admin/members/lifeevent/{instance.pk}/change/"
            )
        
        # Créer automatiquement une visite "À FAIRE"
        if instance.requires_visit:
            # Trouver le pasteur principal (premier superuser)
            main_pastor = User.objects.filter(is_superuser=True, is_active=True).first()
            
            VisitationLog.objects.create(
                visitor=main_pastor,
                member=instance.primary_member,
                visit_type='domicile',
                status='a_faire',
                life_event=instance,
                summary=f"Visite suite au décès : {instance.title}"
            )
    
    elif instance.event_type == 'hospitalisation':
        for pastor in pastors:
            Notification.objects.create(
                user=pastor,
                title=f"🏥 Hospitalisation : {instance.primary_member.full_name}",
                message=f"{instance.primary_member.full_name} est hospitalisé(e). "
                        f"Une visite est recommandée.",
                notification_type='warning',
                action_url=f"/admin/members/lifeevent/{instance.pk}/change/"
            )
        
        # Créer une visite à l'hôpital
        if instance.requires_visit:
            main_pastor = User.objects.filter(is_superuser=True, is_active=True).first()
            
            VisitationLog.objects.create(
                visitor=main_pastor,
                member=instance.primary_member,
                visit_type='hopital',
                status='a_faire',
                life_event=instance,
                summary=f"Visite hospitalière : {instance.description or instance.title}"
            )
    
    elif instance.event_type == 'mariage':
        for pastor in pastors:
            Notification.objects.create(
                user=pastor,
                title=f"💒 Mariage à annoncer : {instance.title}",
                message=f"Un mariage a été enregistré. Pensez à féliciter le couple "
                        f"et à l'annoncer lors du prochain culte.",
                notification_type='success',
                action_url=f"/admin/members/lifeevent/{instance.pk}/change/"
            )
    
    elif instance.event_type == 'bapteme':
        for pastor in pastors:
            Notification.objects.create(
                user=pastor,
                title=f"💧 Baptême : {instance.primary_member.full_name}",
                message=f"Un baptême a été enregistré pour {instance.primary_member.full_name}.",
                notification_type='success',
                action_url=f"/admin/members/lifeevent/{instance.pk}/change/"
            )


@receiver(post_save, sender='members.VisitationLog')
def handle_visit_completion(sender, instance, created, **kwargs):
    """
    Notifie quand une visite est marquée comme effectuée.
    """
    if created:
        return
    
    # Vérifier si le statut vient de passer à "effectue"
    if instance.status == 'effectue' and instance.life_event:
        # Marquer l'événement de vie comme visité
        instance.life_event.visit_completed = True
        instance.life_event.save(update_fields=['visit_completed'])


# =============================================================================
# TÂCHES CELERY POUR LES RAPPELS PÉRIODIQUES
# =============================================================================

def get_members_needing_visit():
    """
    Règle 3 : Retourne les membres non visités depuis 6 mois.
    
    À appeler depuis une tâche Celery hebdomadaire.
    """
    from apps.members.models import Member
    from datetime import date, timedelta
    
    six_months_ago = date.today() - timedelta(days=180)
    
    members_needing_visit = []
    
    for member in Member.objects.filter(status='actif'):
        last_visit = member.last_visit_date
        
        if last_visit is None or last_visit < six_months_ago:
            members_needing_visit.append({
                'member': member,
                'last_visit': last_visit,
                'days_since': member.days_since_last_visit
            })
    
    return members_needing_visit


def send_weekly_visit_reminder():
    """
    Envoie un rappel hebdomadaire avec la liste des membres à visiter.
    
    À appeler depuis Celery Beat (ex: tous les lundis à 8h).
    """
    from apps.communication.models import Notification
    from apps.accounts.models import User
    
    members = get_members_needing_visit()
    
    if not members:
        return
    
    # Construire le message
    message_lines = [f"📋 {len(members)} membre(s) n'ont pas été visités depuis plus de 6 mois :\n"]
    
    for item in members[:10]:  # Limiter à 10 dans la notification
        member = item['member']
        days = item['days_since']
        if days:
            message_lines.append(f"• {member.full_name} ({days} jours)")
        else:
            message_lines.append(f"• {member.full_name} (jamais visité)")
    
    if len(members) > 10:
        message_lines.append(f"\n... et {len(members) - 10} autres.")
    
    message = "\n".join(message_lines)
    
    # Notifier les pasteurs
    pastors = User.objects.filter(role__icontains='pasteur', is_active=True) | User.objects.filter(role__icontains='admin', is_active=True)
    
    for pastor in pastors:
        Notification.objects.create(
            user=pastor,
            title="📅 Rappel hebdomadaire : Visites pastorales",
            message=message,
            notification_type='info',
            action_url="/admin/members/visitationlog/?status=a_faire"
        )


# =============================================================================
# TÂCHE CELERY (à ajouter dans gestion_eebc/celery.py)
# =============================================================================
"""
Pour activer le rappel hebdomadaire, ajouter dans gestion_eebc/celery.py :

from celery.schedules import crontab

app.conf.beat_schedule = {
    'weekly-visit-reminder': {
        'task': 'apps.communication.tasks.weekly_visit_reminder_task',
        'schedule': crontab(hour=8, minute=0, day_of_week=1),  # Lundi 8h
    },
}

Et créer apps/communication/tasks.py :

from celery import shared_task
from apps.communication.signals import send_weekly_visit_reminder

@shared_task
def weekly_visit_reminder_task():
    send_weekly_visit_reminder()
"""
