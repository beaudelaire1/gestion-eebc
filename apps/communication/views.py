from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import date

from .models import Notification, Announcement, EmailLog, SMSLog


@login_required
def notifications_list(request):
    """Liste des notifications de l'utilisateur."""
    notifications = request.user.notifications.all().order_by('-created_at')
    
    # Filtres
    notif_type = request.GET.get('type')
    is_read = request.GET.get('is_read')
    
    if notif_type:
        notifications = notifications.filter(notification_type=notif_type)
    if is_read == 'false':
        notifications = notifications.filter(is_read=False)
    elif is_read == 'true':
        notifications = notifications.filter(is_read=True)
    
    unread_count = request.user.notifications.filter(is_read=False).count()
    
    context = {
        'notifications': notifications[:100],
        'unread_count': unread_count,
        'notification_types': Notification.NotificationType.choices if hasattr(Notification, 'NotificationType') else [],
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'communication/partials/notifications_list.html', context)
    return render(request, 'communication/notifications.html', context)


@login_required
def notification_detail(request, pk):
    """Détail et marquage comme lu d'une notification."""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.mark_as_read()
    
    if request.headers.get('HX-Request'):
        return render(request, 'communication/partials/notification_item.html', {'notification': notification})
    return render(request, 'communication/notification_detail.html', {'notification': notification})


@login_required
def notification_mark_read(request, pk):
    """Marquer une notification comme lue."""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.mark_as_read()
    
    if request.headers.get('HX-Request'):
        return JsonResponse({'success': True})
    return redirect('communication:notifications')


@login_required
def notifications_mark_all_read(request):
    """Marquer toutes les notifications comme lues."""
    request.user.notifications.filter(is_read=False).update(
        is_read=True, 
        read_at=timezone.now()
    )
    messages.success(request, "Toutes les notifications ont été marquées comme lues.")
    return redirect('communication:notifications')


@login_required
def notifications_count(request):
    """Nombre de notifications non lues (API JSON)."""
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({'count': count})


@login_required
def announcements_list(request):
    """Liste des annonces."""
    from django.db.models import Q
    today = date.today()
    
    # Annonces actives
    active_announcements = Announcement.objects.filter(
        is_active=True
    ).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=today)
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=today)
    ).order_by('-is_pinned', '-created_at')
    
    # Toutes les annonces pour les admins
    all_announcements = None
    if request.user.is_staff:
        all_announcements = Announcement.objects.all().order_by('-created_at')
    
    context = {
        'announcements': active_announcements,
        'all_announcements': all_announcements,
    }
    
    return render(request, 'communication/announcements.html', context)


@login_required
def announcement_create(request):
    """Créer une annonce."""
    if not request.user.is_staff:
        messages.error(request, "Vous n'avez pas la permission de créer des annonces.")
        return redirect('communication:announcements')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        is_pinned = 'is_pinned' in request.POST
        start_date = request.POST.get('start_date') or None
        end_date = request.POST.get('end_date') or None
        
        announcement = Announcement.objects.create(
            title=title,
            content=content,
            is_pinned=is_pinned,
            start_date=start_date,
            end_date=end_date,
            author=request.user,
            is_active=True
        )
        
        messages.success(request, f"Annonce '{title}' créée avec succès.")
        return redirect('communication:announcements')
    
    return render(request, 'communication/announcement_create.html')


@login_required
def announcement_detail(request, pk):
    """Détail d'une annonce."""
    announcement = get_object_or_404(Announcement, pk=pk)
    return render(request, 'communication/announcement_detail.html', {'announcement': announcement})


@login_required
def email_logs(request):
    """Logs des emails envoyés."""
    if not request.user.is_staff:
        messages.error(request, "Accès réservé aux administrateurs.")
        return redirect('dashboard:home')
    
    logs = EmailLog.objects.all().order_by('-created_at')
    
    # Filtres
    status = request.GET.get('status')
    if status:
        logs = logs.filter(status=status)
    
    context = {
        'logs': logs[:200],
        'statuses': EmailLog.Status.choices if hasattr(EmailLog, 'Status') else [],
    }
    
    return render(request, 'communication/email_logs.html', context)


@login_required
def sms_logs(request):
    """Logs des SMS envoyés."""
    if not request.user.is_staff:
        messages.error(request, "Accès réservé aux administrateurs.")
        return redirect('dashboard:home')
    
    logs = SMSLog.objects.all().order_by('-created_at')
    
    context = {
        'logs': logs[:200],
    }
    
    return render(request, 'communication/sms_logs.html', context)


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

