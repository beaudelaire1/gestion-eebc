from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone

from .models import Notification, Announcement


@login_required
def notifications_list(request):
    """Liste des notifications de l'utilisateur."""
    notifications = request.user.notifications.all()
    
    # Marquer comme lues si demandé
    if request.GET.get('mark_all_read'):
        notifications.filter(is_read=False).update(is_read=True, read_at=timezone.now())
    
    unread_count = notifications.filter(is_read=False).count()
    
    context = {
        'notifications': notifications[:50],
        'unread_count': unread_count,
    }
    
    if request.htmx:
        return render(request, 'communication/partials/notifications_list.html', context)
    return render(request, 'communication/notifications.html', context)


@login_required
def notification_detail(request, pk):
    """Détail et marquage comme lu d'une notification."""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.mark_as_read()
    
    if request.htmx:
        return render(request, 'communication/partials/notification_item.html', {'notification': notification})
    return render(request, 'communication/notification_detail.html', {'notification': notification})


@login_required
def notifications_count(request):
    """Nombre de notifications non lues (API JSON)."""
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({'count': count})


@login_required
def announcements_list(request):
    """Liste des annonces actives."""
    from datetime import date
    from django.db.models import Q
    today = date.today()
    
    announcements = Announcement.objects.filter(
        is_active=True
    ).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=today)
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=today)
    )
    
    return render(request, 'communication/announcements.html', {'announcements': announcements})


def send_notification(user, title, message, notification_type='info', link=''):
    """
    Fonction utilitaire pour créer une notification.
    """
    return Notification.objects.create(
        recipient=user,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link
    )


def send_email_notification(recipient_email, recipient_name, subject, body):
    """
    Fonction utilitaire pour envoyer un email (utilise le backend console en dev).
    """
    from django.core.mail import send_mail
    from .models import EmailLog
    
    log = EmailLog.objects.create(
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        subject=subject,
        body=body
    )
    
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=None,  # Utilise DEFAULT_FROM_EMAIL
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        log.status = 'sent'
        log.sent_at = timezone.now()
    except Exception as e:
        log.status = 'failed'
        log.error_message = str(e)
    
    log.save()
    return log

