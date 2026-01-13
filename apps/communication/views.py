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
    # Utiliser le système de rôles du projet
    if request.user.is_admin or request.user.role in ['admin', 'secretariat']:
        all_announcements = Announcement.objects.all().order_by('-created_at')
    
    context = {
        'announcements': active_announcements,
        'all_announcements': all_announcements,
    }
    
    return render(request, 'communication/announcements.html', context)


@login_required
def announcement_create(request):
    """Créer une annonce."""
    # Utiliser le système de rôles du projet au lieu de is_staff
    if not (request.user.is_admin or request.user.role in ['admin', 'secretariat']):
        messages.error(request, "Vous n'avez pas la permission de créer des annonces.")
        return redirect('communication:announcements')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        is_pinned = 'is_pinned' in request.POST
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        # Préparer les données pour la création
        announcement_data = {
            'title': title,
            'content': content,
            'is_pinned': is_pinned,
            'created_by': request.user,
            'is_active': True
        }
        
        # Gérer les dates optionnelles
        if start_date:
            from django.utils.dateparse import parse_date
            parsed_start = parse_date(start_date)
            if parsed_start:
                announcement_data['start_date'] = parsed_start
        
        if end_date:
            from django.utils.dateparse import parse_date
            parsed_end = parse_date(end_date)
            if parsed_end:
                announcement_data['end_date'] = parsed_end
        
        try:
            announcement = Announcement.objects.create(**announcement_data)
            messages.success(request, f"Annonce '{title}' créée avec succès.")
            return redirect('communication:announcements')
        except Exception as e:
            messages.error(request, f"Erreur lors de la création : {e}")
    
    return render(request, 'communication/announcement_create.html')


@login_required
def announcement_detail(request, pk):
    """Détail d'une annonce."""
    announcement = get_object_or_404(Announcement, pk=pk)
    return render(request, 'communication/announcement_detail.html', {'announcement': announcement})


@login_required
def announcement_edit(request, pk):
    """Modifier une annonce."""
    # Utiliser le système de rôles du projet
    if not (request.user.is_admin or request.user.role in ['admin', 'secretariat']):
        messages.error(request, "Vous n'avez pas la permission de modifier des annonces.")
        return redirect('communication:announcements')
    
    announcement = get_object_or_404(Announcement, pk=pk)
    
    if request.method == 'POST':
        announcement.title = request.POST.get('title')
        announcement.content = request.POST.get('content')
        announcement.is_pinned = 'is_pinned' in request.POST
        announcement.is_active = 'is_active' in request.POST
        
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        if start_date:
            announcement.start_date = start_date
        if end_date:
            announcement.end_date = end_date
        
        announcement.save()
        
        messages.success(request, f"Annonce '{announcement.title}' modifiée avec succès.")
        return redirect('communication:announcement_detail', pk=announcement.pk)
    
    return render(request, 'communication/announcement_edit.html', {'announcement': announcement})


@login_required
def announcement_delete(request, pk):
    """Supprimer une annonce."""
    # Utiliser le système de rôles du projet
    if not (request.user.is_admin or request.user.role in ['admin', 'secretariat']):
        messages.error(request, "Vous n'avez pas la permission de supprimer des annonces.")
        return redirect('communication:announcements')
    
    announcement = get_object_or_404(Announcement, pk=pk)
    
    if request.method == 'POST':
        title = announcement.title
        announcement.delete()
        messages.success(request, f"Annonce '{title}' supprimée avec succès.")
        return redirect('communication:announcements')
    
    return render(request, 'communication/announcement_delete.html', {'announcement': announcement})


@login_required
def announcement_toggle_active(request, pk):
    """Activer/désactiver une annonce."""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Permission refusée'})
    
    announcement = get_object_or_404(Announcement, pk=pk)
    announcement.is_active = not announcement.is_active
    announcement.save()
    
    status = "activée" if announcement.is_active else "désactivée"
    messages.success(request, f"Annonce '{announcement.title}' {status}.")
    
    if request.headers.get('HX-Request'):
        return JsonResponse({'success': True, 'is_active': announcement.is_active})
    return redirect('communication:announcements')


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
        'statuses': EmailLog.Status.choices,
        'total_count': EmailLog.objects.count(),
    }
    
    return render(request, 'communication/email_logs.html', context)


@login_required
def email_log_delete(request, pk):
    """Supprimer un log d'email."""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Permission refusée'})
    
    log = get_object_or_404(EmailLog, pk=pk)
    
    if request.method == 'POST':
        log.delete()
        messages.success(request, "Log d'email supprimé avec succès.")
        
        if request.headers.get('HX-Request'):
            return JsonResponse({'success': True})
        return redirect('communication:email_logs')
    
    return render(request, 'communication/email_log_delete.html', {'log': log})


@login_required
def email_logs_clear_old(request):
    """Supprimer les anciens logs d'emails (plus de 30 jours)."""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Permission refusée'})
    
    if request.method == 'POST':
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=30)
        deleted_count = EmailLog.objects.filter(created_at__lt=cutoff_date).count()
        EmailLog.objects.filter(created_at__lt=cutoff_date).delete()
        
        messages.success(request, f"{deleted_count} anciens logs d'emails supprimés.")
        
        if request.headers.get('HX-Request'):
            return JsonResponse({'success': True, 'deleted_count': deleted_count})
        return redirect('communication:email_logs')
    
    # Compter les logs anciens
    from datetime import timedelta
    cutoff_date = timezone.now() - timedelta(days=30)
    old_logs_count = EmailLog.objects.filter(created_at__lt=cutoff_date).count()
    
    return render(request, 'communication/email_logs_clear.html', {'old_logs_count': old_logs_count})


@login_required
def sms_logs(request):
    """Logs des SMS envoyés."""
    if not request.user.is_staff:
        messages.error(request, "Accès réservé aux administrateurs.")
        return redirect('dashboard:home')
    
    logs = SMSLog.objects.all().order_by('-created_at')
    
    context = {
        'logs': logs[:200],
        'total_count': SMSLog.objects.count(),
    }
    
    return render(request, 'communication/sms_logs.html', context)


@login_required
def sms_log_delete(request, pk):
    """Supprimer un log de SMS."""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Permission refusée'})
    
    log = get_object_or_404(SMSLog, pk=pk)
    
    if request.method == 'POST':
        log.delete()
        messages.success(request, "Log de SMS supprimé avec succès.")
        
        if request.headers.get('HX-Request'):
            return JsonResponse({'success': True})
        return redirect('communication:sms_logs')
    
    return render(request, 'communication/sms_log_delete.html', {'log': log})


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

