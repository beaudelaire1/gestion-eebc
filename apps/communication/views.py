from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Q
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import hashlib
import hmac
import json
import logging

from .models import Notification, Announcement, EmailLog, SMSLog
from .forms import AnnouncementForm, ComposeEmailForm, EmailLogFilterForm, SMSLogFilterForm
from .services import send_whatsapp_announcement

logger = logging.getLogger(__name__)


def _is_comm_admin(user):
    """Vérifie si l'utilisateur a les droits d'administration communication."""
    return user.is_admin or user.has_any_role('admin', 'secretariat', 'pasteur')


@login_required
def email_smtp_diagnostic(request):
    """Diagnostic SMTP : teste la connexion et l'authentification de chaque boîte.
    
    N'envoie aucun e-mail. Pour chaque département actif :
      1. Vérifie la présence du mot de passe en variable d'environnement.
      2. Teste la connexion TCP + STARTTLS vers le serveur SMTP.
      3. Teste l'authentification (login) avec les identifiants de la boîte.
    Affiche le verdict exact renvoyé par le serveur (utile en production
    où aucun shell n'est disponible).
    """
    import os
    import smtplib

    from .models import EmailSenderDepartment

    if not _is_comm_admin(request.user):
        messages.error(request, "Vous n'avez pas accès au diagnostic e-mail.")
        return redirect('dashboard:home')
    
    host = getattr(settings, 'HOSTINGER_EMAIL_HOST', 'smtp.hostinger.com')
    port = getattr(settings, 'HOSTINGER_EMAIL_PORT', 587)
    use_tls = getattr(settings, 'HOSTINGER_EMAIL_USE_TLS', True)
    use_ssl = getattr(settings, 'HOSTINGER_EMAIL_USE_SSL', False)
    
    backend_env = os.environ.get('EMAIL_BACKEND', 'console')
    results = []
    
    for dept in EmailSenderDepartment.objects.filter(is_active=True).order_by('order'):
        entry = {
            'department': dept,
            'env_var': dept.smtp_password_env_name,
            'password_found': False,
            'connection_ok': False,
            'auth_ok': False,
            'error': '',
        }
        password = os.environ.get(dept.smtp_password_env_name, '') or \
            os.environ.get(dept.smtp_password_legacy_env_name, '')
        entry['password_found'] = bool(password)
        
        if password:
            try:
                if use_ssl:
                    smtp = smtplib.SMTP_SSL(host, port, timeout=15)
                else:
                    smtp = smtplib.SMTP(host, port, timeout=15)
                    if use_tls:
                        smtp.starttls()
                entry['connection_ok'] = True
                try:
                    smtp.login(dept.from_email, password)
                    entry['auth_ok'] = True
                except smtplib.SMTPAuthenticationError as e:
                    entry['error'] = f"Authentification refusée ({e.smtp_code}) : {e.smtp_error.decode(errors='replace') if isinstance(e.smtp_error, bytes) else e.smtp_error}"
                except Exception as e:
                    entry['error'] = f"Erreur login : {e}"
                finally:
                    try:
                        smtp.quit()
                    except Exception:
                        pass
            except Exception as e:
                entry['error'] = f"Connexion impossible à {host}:{port} : {e}"
        else:
            entry['error'] = (
                f"Variable {dept.smtp_password_env_name} absente — "
                "fallback sur la boîte par défaut (contact@)."
            )
        
        results.append(entry)
    
    # Test de la boîte par défaut (settings Hostinger)
    default_entry = {
        'department': None,
        'env_var': 'HOSTINGER_EMAIL_HOST_USER / HOSTINGER_EMAIL_HOST_PASSWORD',
        'username': getattr(settings, 'HOSTINGER_EMAIL_HOST_USER', ''),
        'password_found': bool(getattr(settings, 'HOSTINGER_EMAIL_HOST_PASSWORD', '')),
        'connection_ok': False,
        'auth_ok': False,
        'error': '',
    }
    if default_entry['username'] and default_entry['password_found']:
        try:
            if use_ssl:
                smtp = smtplib.SMTP_SSL(host, port, timeout=15)
            else:
                smtp = smtplib.SMTP(host, port, timeout=15)
                if use_tls:
                    smtp.starttls()
            default_entry['connection_ok'] = True
            try:
                smtp.login(
                    settings.HOSTINGER_EMAIL_HOST_USER,
                    settings.HOSTINGER_EMAIL_HOST_PASSWORD,
                )
                default_entry['auth_ok'] = True
            except smtplib.SMTPAuthenticationError as e:
                default_entry['error'] = f"Authentification refusée ({e.smtp_code}) : {e.smtp_error.decode(errors='replace') if isinstance(e.smtp_error, bytes) else e.smtp_error}"
            except Exception as e:
                default_entry['error'] = f"Erreur login : {e}"
            finally:
                try:
                    smtp.quit()
                except Exception:
                    pass
        except Exception as e:
            default_entry['error'] = f"Connexion impossible à {host}:{port} : {e}"
    else:
        default_entry['error'] = "HOSTINGER_EMAIL_HOST_USER ou HOSTINGER_EMAIL_HOST_PASSWORD manquant."
    
    context = {
        'results': results,
        'default_entry': default_entry,
        'smtp_host': host,
        'smtp_port': port,
        'use_tls': use_tls,
        'use_ssl': use_ssl,
        'backend_env': backend_env,
        'email_backend': settings.EMAIL_BACKEND,
    }
    return render(request, 'communication/email_smtp_diagnostic.html', context)


@login_required
def email_compose(request):
    """Éditeur d'e-mails : composition et envoi avec département expéditeur."""
    if not _is_comm_admin(request.user):
        messages.error(request, "Vous n'avez pas accès à l'éditeur d'e-mails.")
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = ComposeEmailForm(request.POST, request.FILES)
        if form.is_valid():
            from apps.core.templatetags.sanitize_tags import sanitize_html
            from .services import EmailService
            
            department = form.cleaned_data['department']
            subject = form.cleaned_data['subject']
            body_html = sanitize_html(form.cleaned_data['body'])
            # Connexion SMTP de la boîte du département (None = boîte par défaut)
            connection = department.get_smtp_connection()
            
            # Pièces jointes lues une seule fois, partagées entre les envois
            attachments = [
                (f.name, f.read(), f.content_type or 'application/octet-stream')
                for f in form.cleaned_data['attachments']
            ]
            cc = form.cleaned_data['cc']
            bcc = form.cleaned_data['bcc']
            # Reply-To pointe toujours vers la vraie boîte du département.
            # Indispensable quand le fallback contact@ est utilisé :
            # les réponses arrivent au bon département même si l'envoi
            # transite par la boîte par défaut.
            reply_to = [department.from_email]
            
            # Destinataires : comptes d'équipe + adresses externes
            raw_targets = [
                (user.email, user.get_full_name() or user.username)
                for user in form.cleaned_data['recipients']
            ]
            raw_targets += [(email, '') for email in form.cleaned_data['external_recipients']]

            # Dédoublonnage strict (insensible à la casse) pour éviter les doubles
            # envois quand la même adresse est saisie en interne + externe.
            targets = []
            seen_targets = {}
            duplicate_targets = 0
            for email_address, full_name in raw_targets:
                normalized_email = (email_address or '').strip().lower()
                if not normalized_email:
                    continue

                if normalized_email in seen_targets:
                    duplicate_targets += 1
                    existing_idx = seen_targets[normalized_email]
                    existing_email, existing_name = targets[existing_idx]
                    # Conserver le nom le plus informatif quand possible.
                    if not existing_name and full_name:
                        targets[existing_idx] = (existing_email, full_name)
                    continue

                seen_targets[normalized_email] = len(targets)
                targets.append(((email_address or '').strip(), full_name))

            if not targets:
                messages.error(request, "Aucun destinataire valide après normalisation.")
                return render(request, 'communication/email_compose.html', {'form': form})

            # Dédoublonnage CC/CCI et exclusion de la même adresse que le TO.
            # (sinon certains clients affichent des doublons de réception)
            dedup_cc = []
            dedup_bcc = []
            seen_cc = set()
            seen_bcc = set()
            for cc_email in cc:
                cc_norm = cc_email.strip().lower()
                if cc_norm and cc_norm not in seen_cc:
                    seen_cc.add(cc_norm)
                    dedup_cc.append(cc_email.strip())
            for bcc_email in bcc:
                bcc_norm = bcc_email.strip().lower()
                if bcc_norm and bcc_norm not in seen_bcc:
                    seen_bcc.add(bcc_norm)
                    dedup_bcc.append(bcc_email.strip())
            
            sent, failed = 0, 0
            last_error = ''
            for email_address, full_name in targets:
                recipient_norm = email_address.strip().lower()
                filtered_cc = [item for item in dedup_cc if item.strip().lower() != recipient_norm]
                filtered_bcc = [item for item in dedup_bcc if item.strip().lower() != recipient_norm]

                email_log = EmailService.send_email(
                    recipient_email=email_address,
                    subject=subject,
                    template_name='emails/composed_message.html',
                    context={
                        'body_html': body_html,
                        'department': department,
                        'recipient_name': full_name,
                        'subject': subject,
                    },
                    recipient_name=full_name,
                    from_email=department.sender_header,
                    fail_silently=True,
                    connection=connection,
                    attachments=attachments,
                    cc=filtered_cc,
                    bcc=filtered_bcc,
                    reply_to=reply_to,
                )
                if email_log.status == EmailLog.Status.SENT:
                    sent += 1
                else:
                    failed += 1
                    if email_log.error_message:
                        last_error = email_log.error_message
            
            if sent:
                messages.success(request, f"{sent} e-mail(s) envoyé(s) depuis « {department.name} ».")
            if duplicate_targets:
                messages.info(
                    request,
                    f"{duplicate_targets} destinataire(s) en doublon ignoré(s) (même adresse saisie plusieurs fois).",
                )
            if failed:
                detail = f" Cause : {last_error}" if last_error else ''
                messages.error(
                    request,
                    f"{failed} envoi(s) en échec — voir l'historique des e-mails.{detail}",
                )
            return redirect('communication:email_logs')
    else:
        form = ComposeEmailForm()
    
    return render(request, 'communication/email_compose.html', {'form': form})


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
        'notification_types': Notification.Type.choices,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'communication/partials/notifications_list.html', context)
    return render(request, 'communication/notifications.html', context)


@login_required
def notification_detail(request, pk):
    """Détail et marquage comme lu d'une notification."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.mark_as_read()
    
    if request.headers.get('HX-Request'):
        return render(request, 'communication/partials/notification_item.html', {'notification': notification})
    return render(request, 'communication/notification_detail.html', {'notification': notification})


@login_required
def notification_mark_read(request, pk):
    """Marquer une notification comme lue."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
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
    now = timezone.now()
    
    # Annonces actives
    active_announcements = Announcement.objects.filter(
        is_active=True
    ).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=now)
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=now)
    ).order_by('-is_pinned', '-created_at')
    
    # Toutes les annonces pour les admins
    all_announcements = None
    # Utiliser le système de rôles du projet
    if request.user.is_admin or request.user.has_any_role('admin', 'secretariat'):
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
    if not (request.user.is_admin or request.user.has_any_role('admin', 'secretariat')):
        messages.error(request, "Vous n'avez pas la permission de créer des annonces.")
        return redirect('communication:announcements')
    
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.created_by = request.user
            announcement.save()

            if announcement.notify_by_sms:
                result = send_whatsapp_announcement(announcement)
                if result['total'] == 0:
                    messages.warning(request, "Aucun destinataire WhatsApp éligible n'a été trouvé.")
                elif result['failed'] == 0:
                    messages.success(
                        request,
                        f"WhatsApp envoyé à {result['sent']} destinataire(s)."
                    )
                else:
                    messages.warning(
                        request,
                        f"WhatsApp partiel: {result['sent']} envoyé(s), {result['failed']} échec(s)."
                    )

            messages.success(request, f"Annonce '{announcement.title}' créée avec succès.")
            return redirect('communication:announcements')
        else:
            for error in form.errors.values():
                messages.error(request, error.as_text())
    else:
        form = AnnouncementForm()
    
    return render(request, 'communication/announcement_create.html', {'form': form})


@login_required
def announcement_detail(request, pk):
    """Détail d'une annonce."""
    announcement = get_object_or_404(Announcement, pk=pk)
    return render(request, 'communication/announcement_detail.html', {'announcement': announcement})


@login_required
def announcement_edit(request, pk):
    """Modifier une annonce."""
    # Utiliser le système de rôles du projet
    if not (request.user.is_admin or request.user.has_any_role('admin', 'secretariat')):
        messages.error(request, "Vous n'avez pas la permission de modifier des annonces.")
        return redirect('communication:announcements')
    
    announcement = get_object_or_404(Announcement, pk=pk)
    
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            form.save()
            messages.success(request, f"Annonce '{announcement.title}' modifiée avec succès.")
            return redirect('communication:announcement_detail', pk=announcement.pk)
        else:
            for error in form.errors.values():
                messages.error(request, error.as_text())
    else:
        form = AnnouncementForm(instance=announcement)
    
    return render(request, 'communication/announcement_edit.html', {
        'announcement': announcement,
        'form': form,
    })


@login_required
def announcement_delete(request, pk):
    """Supprimer une annonce."""
    # Utiliser le système de rôles du projet
    if not (request.user.is_admin or request.user.has_any_role('admin', 'secretariat')):
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
    if not _is_comm_admin(request.user):
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
    """Logs des emails envoyés avec suppression en masse."""
    if not _is_comm_admin(request.user):
        messages.error(request, "Accès réservé aux administrateurs.")
        return redirect('dashboard:home')

    # Traitement de la suppression en masse (POST)
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_logs')
        if not selected_ids:
            messages.warning(request, "Veuillez sélectionner au moins un log à supprimer.")
        else:
            try:
                count = EmailLog.objects.filter(id__in=selected_ids).count()
                EmailLog.objects.filter(id__in=selected_ids).delete()
                messages.success(request, f"{count} log(s) email supprimé(s) avec succès.")
            except Exception as e:
                messages.error(request, f"Erreur lors de la suppression : {str(e)}")
        return redirect('communication:email_logs')

    # GET - affichage et filtres
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '')

    logs = EmailLog.objects.all().order_by('-created_at')

    if status_filter:
        logs = logs.filter(status=status_filter)
    if search:
        logs = logs.filter(
            Q(recipient_email__icontains=search)
            | Q(subject__icontains=search)
            | Q(recipient_name__icontains=search)
        )

    paginator = Paginator(logs, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    stats = {
        'total': EmailLog.objects.count(),
        'sent': EmailLog.objects.filter(status=EmailLog.Status.SENT).count(),
        'failed': EmailLog.objects.filter(status=EmailLog.Status.FAILED).count(),
        'pending': EmailLog.objects.filter(status=EmailLog.Status.PENDING).count(),
    }

    context = {
        'page_obj': page_obj,
        'logs': page_obj.object_list,
        'stats': stats,
        'status_filter': status_filter,
        'search': search,
        'statuses': EmailLog.Status.choices,
        'total_count': EmailLog.objects.count(),
    }

    return render(request, 'communication/email_logs.html', context)


@login_required
def email_log_delete(request, pk):
    """Supprimer un log d'email."""
    if not _is_comm_admin(request.user):
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
    if not _is_comm_admin(request.user):
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
    if not _is_comm_admin(request.user):
        messages.error(request, "Accès réservé aux administrateurs.")
        return redirect('dashboard:home')
    
    logs = SMSLog.objects.all().order_by('-created_at')
    filter_form = SMSLogFilterForm(request.GET or None)
    
    if filter_form.is_valid():
        status = filter_form.cleaned_data.get('status')
        phone = filter_form.cleaned_data.get('phone')
        from_date = filter_form.cleaned_data.get('from_date')
        to_date = filter_form.cleaned_data.get('to_date')
        
        if status:
            logs = logs.filter(status=status)
        if phone:
            logs = logs.filter(recipient_phone__icontains=phone)
        if from_date:
            logs = logs.filter(created_at__date__gte=from_date)
        if to_date:
            logs = logs.filter(created_at__date__lte=to_date)
    
    paginator = Paginator(logs, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    
    context = {
        'logs': page_obj,
        'page_obj': page_obj,
        'filter_form': filter_form,
        'total_count': SMSLog.objects.count(),
    }
    
    return render(request, 'communication/sms_logs.html', context)


@login_required
def sms_log_delete(request, pk):
    """Supprimer un log de SMS."""
    if not _is_comm_admin(request.user):
        return JsonResponse({'success': False, 'error': 'Permission refusée'})
    
    log = get_object_or_404(SMSLog, pk=pk)
    
    if request.method == 'POST':
        log.delete()
        messages.success(request, "Log de SMS supprimé avec succès.")
        
        if request.headers.get('HX-Request'):
            return JsonResponse({'success': True})
        return redirect('communication:sms_logs')
    
    return render(request, 'communication/sms_log_delete.html', {'log': log})


@csrf_exempt
def whatsapp_webhook(request):
    """Webhook Meta WhatsApp Cloud API avec vérification HMAC."""
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == settings.META_WHATSAPP_VERIFY_TOKEN:
            return HttpResponse(challenge, content_type="text/plain", status=200)

        return HttpResponse("Invalid verify token", status=403)

    if request.method == "POST":
        # Vérification de la signature HMAC X-Hub-Signature-256
        app_secret = getattr(settings, 'META_WHATSAPP_APP_SECRET', '')
        if app_secret:
            signature_header = request.headers.get('X-Hub-Signature-256', '')
            if not signature_header.startswith('sha256='):
                logger.warning("WhatsApp webhook: signature HMAC manquante")
                return HttpResponse("Missing signature", status=403)
            expected = hmac.new(
                app_secret.encode('utf-8'),
                request.body,
                hashlib.sha256,
            ).hexdigest()
            received = signature_header[7:]  # strip "sha256="
            if not hmac.compare_digest(expected, received):
                logger.warning("WhatsApp webhook: signature HMAC invalide")
                return HttpResponse("Invalid signature", status=403)

        logger.info("WhatsApp webhook: message reçu")
        return JsonResponse({"status": "received"}, status=200)

    return HttpResponse(status=405)


def send_notification(user, title, message, notification_type='info', link=''):
    """
    Fonction utilitaire pour créer une notification.
    """
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        action_url=link
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


# =============================================================================
# GESTION DES LOGS EMAILS - SUPPRESSION AVEC CHECKBOXES
# =============================================================================

@login_required
def email_logs_management(request):
    """
    Affiche la liste des logs emails avec des checkboxes pour suppression.
    """
    from django.core.paginator import Paginator
    
    # Vérifier les permissions
    if not request.user.has_role('admin'):
        messages.error(request, "Vous n'avez pas accès à cette page.")
        return redirect('dashboard:index')
    
    # Traitement de la suppression (POST)
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_logs')
        
        if not selected_ids:
            messages.warning(request, "Veuillez sélectionner au moins un log à supprimer.")
            return redirect('communication:email_logs_management')
        
        try:
            # Récupérer les logs à supprimer
            logs_to_delete = EmailLog.objects.filter(id__in=selected_ids)
            count = logs_to_delete.count()
            
            # Supprimer
            logs_to_delete.delete()
            
            messages.success(request, f"✅ {count} log(s) email supprimé(s) avec succès.")
        except Exception as e:
            messages.error(request, f"❌ Erreur lors de la suppression: {str(e)}")
        
        return redirect('communication:email_logs_management')
    
    # GET - Afficher les logs
    # Filtres
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    logs = EmailLog.objects.all().order_by('-created_at')
    
    if status_filter:
        logs = logs.filter(status=status_filter)
    
    if search:
        logs = logs.filter(
            Q(recipient_email__icontains=search) |
            Q(subject__icontains=search) |
            Q(recipient_name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Statistiques
    stats = {
        'total': EmailLog.objects.count(),
        'sent': EmailLog.objects.filter(status=EmailLog.Status.SENT).count(),
        'failed': EmailLog.objects.filter(status=EmailLog.Status.FAILED).count(),
        'pending': EmailLog.objects.filter(status=EmailLog.Status.PENDING).count(),
        'others': EmailLog.objects.exclude(status__in=[
            EmailLog.Status.SENT, EmailLog.Status.FAILED, EmailLog.Status.PENDING
        ]).count(),
    }
    
    context = {
        'page_obj': page_obj,
        'logs': page_obj.object_list,
        'stats': stats,
        'status_filter': status_filter,
        'search': search,
        'statuses': EmailLog.Status.choices,
    }
    
    return render(request, 'communication/email_logs_management.html', context)
