from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from apps.core.permissions import role_required
from .models import DriverProfile, TransportRequest, DriverLiveLocation
from .forms import DriverProfileForm, TransportRequestForm, DriverAssignmentForm
import logging

logger = logging.getLogger(__name__)


@login_required
@role_required('admin', 'secretariat', 'responsable_groupe')
def driver_list(request):
    """Liste des chauffeurs."""
    drivers = DriverProfile.objects.select_related('user').all()
    return render(request, 'transport/driver_list.html', {'drivers': drivers})


@login_required
@role_required('admin', 'secretariat', 'responsable_groupe')
def driver_create(request):
    """Créer un nouveau profil chauffeur."""
    if request.method == 'POST':
        form = DriverProfileForm(request.POST)
        if form.is_valid():
            driver = form.save()
            messages.success(request, f'Profil chauffeur créé pour {driver.user.get_full_name()}.')
            return redirect('transport:drivers')
    else:
        form = DriverProfileForm()
    
    return render(request, 'transport/driver_form.html', {
        'form': form,
        'title': 'Nouveau chauffeur',
        'submit_text': 'Créer'
    })


@login_required
@role_required('admin', 'secretariat', 'responsable_groupe')
def driver_update(request, pk):
    """Modifier un profil chauffeur."""
    driver = get_object_or_404(DriverProfile, pk=pk)
    
    if request.method == 'POST':
        form = DriverProfileForm(request.POST, instance=driver)
        if form.is_valid():
            driver = form.save()
            messages.success(request, f'Profil chauffeur mis à jour pour {driver.user.get_full_name()}.')
            return redirect('transport:drivers')
    else:
        form = DriverProfileForm(instance=driver)
    
    return render(request, 'transport/driver_form.html', {
        'form': form,
        'driver': driver,
        'title': f'Modifier {driver.user.get_full_name()}',
        'submit_text': 'Mettre à jour'
    })


@login_required
@role_required('admin', 'secretariat', 'responsable_groupe')
def driver_detail(request, pk):
    """Détail d'un chauffeur."""
    driver = get_object_or_404(DriverProfile.objects.select_related('user'), pk=pk)
    recent_requests = driver.transport_requests.order_by('-event_date')[:5]
    
    return render(request, 'transport/driver_detail.html', {
        'driver': driver,
        'recent_requests': recent_requests
    })


@login_required
def transport_requests(request):
    """Liste des demandes de transport."""
    requests_qs = TransportRequest.objects.select_related('driver__user').order_by('-event_date', '-event_time')
    paginator = Paginator(requests_qs, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'transport/transport_requests.html', {'requests': page_obj, 'page_obj': page_obj})


@login_required
def transport_request_create(request):
    """Créer une nouvelle demande de transport."""
    if request.method == 'POST':
        form = TransportRequestForm(request.POST, current_user=request.user)
        if form.is_valid():
            transport_request = form.save()
            messages.success(request, 'Demande de transport créée avec succès.')
            return redirect('transport:requests')
    else:
        form = TransportRequestForm(current_user=request.user)

    return render(request, 'transport/transport_request_form.html', {
        'form': form,
        'title': 'Nouvelle demande de transport',
        'submit_text': 'Créer la demande'
    })


@login_required
@role_required('admin', 'secretariat', 'responsable_groupe')
def transport_request_update(request, pk):
    """Modifier une demande de transport."""
    transport_request = get_object_or_404(TransportRequest, pk=pk)
    
    if request.method == 'POST':
        form = TransportRequestForm(request.POST, instance=transport_request, current_user=request.user)
        if form.is_valid():
            transport_request = form.save()
            messages.success(request, 'Demande de transport mise à jour.')
            return redirect('transport:requests')
    else:
        form = TransportRequestForm(instance=transport_request, current_user=request.user)
    
    return render(request, 'transport/transport_request_form.html', {
        'form': form,
        'transport_request': transport_request,
        'title': f'Modifier la demande de {transport_request.requester_name}',
        'submit_text': 'Mettre à jour'
    })


@login_required
def transport_request_detail(request, pk):
    """Détail d'une demande de transport."""
    transport_request = get_object_or_404(
        TransportRequest.objects.select_related('driver__user'), 
        pk=pk
    )
    
    can_manage_live_tracking = (
        request.user.is_admin
        or request.user.has_any_role('admin', 'secretariat', 'responsable_groupe')
    )
    can_push_live_tracking = bool(
        transport_request.driver
        and (transport_request.driver.user_id == request.user.id or can_manage_live_tracking)
    )

    return render(request, 'transport/transport_request_detail.html', {
        'transport_request': transport_request,
        'can_manage_live_tracking': can_manage_live_tracking,
        'can_push_live_tracking': can_push_live_tracking,
    })


def _can_access_live_tracking(user, transport_request, for_update=False):
    if not user.is_authenticated:
        return False

    if user.is_admin or user.has_any_role('admin', 'secretariat', 'responsable_groupe'):
        return True

    if transport_request.driver and transport_request.driver.user_id == user.id:
        return True

    if for_update:
        return False

    requester_member = transport_request.requester_member
    if requester_member and requester_member.user_id == user.id:
        return True

    return False


def _build_live_payload(transport_request):
    live_location = getattr(transport_request, 'live_location', None)
    if not live_location:
        return {
            'tracking_available': bool(transport_request.driver_id),
            'is_active': False,
            'has_location': False,
            'driver_name': transport_request.driver.user.get_full_name() if transport_request.driver else '',
        }

    now = timezone.now()
    age_seconds = max(int((now - live_location.recorded_at).total_seconds()), 0)

    return {
        'tracking_available': True,
        'is_active': live_location.is_active,
        'has_location': True,
        'driver_name': transport_request.driver.user.get_full_name() if transport_request.driver else '',
        'latitude': float(live_location.latitude),
        'longitude': float(live_location.longitude),
        'speed_kmh': float(live_location.speed_kmh) if live_location.speed_kmh is not None else None,
        'accuracy_m': float(live_location.accuracy_m) if live_location.accuracy_m is not None else None,
        'heading_deg': float(live_location.heading_deg) if live_location.heading_deg is not None else None,
        'recorded_at': live_location.recorded_at.isoformat(),
        'age_seconds': age_seconds,
        'stale': age_seconds > 60,
    }


@login_required
@require_GET
def transport_live_status(request, pk):
    """Retourne la position live d'une demande de transport (JSON)."""
    transport_request = get_object_or_404(
        TransportRequest.objects.select_related('driver__user', 'requester_member__user'),
        pk=pk,
    )

    if not _can_access_live_tracking(request.user, transport_request):
        return JsonResponse({'error': 'Accès refusé'}, status=403)

    return JsonResponse(_build_live_payload(transport_request))


@login_required
@require_POST
def transport_live_update(request, pk):
    """Met à jour la position GPS live d'un chauffeur (JSON)."""
    transport_request = get_object_or_404(
        TransportRequest.objects.select_related('driver__user'),
        pk=pk,
    )

    if not transport_request.driver:
        return JsonResponse({'error': 'Aucun chauffeur assigné'}, status=400)

    if not _can_access_live_tracking(request.user, transport_request, for_update=True):
        return JsonResponse({'error': 'Accès refusé'}, status=403)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalide'}, status=400)

    try:
        latitude = Decimal(str(payload.get('latitude')))
        longitude = Decimal(str(payload.get('longitude')))
    except (InvalidOperation, TypeError, ValueError):
        return JsonResponse({'error': 'Latitude/longitude invalides'}, status=400)

    if latitude < Decimal('-90') or latitude > Decimal('90'):
        return JsonResponse({'error': 'Latitude hors limites'}, status=400)
    if longitude < Decimal('-180') or longitude > Decimal('180'):
        return JsonResponse({'error': 'Longitude hors limites'}, status=400)

    def optional_decimal(name, max_abs=None):
        value = payload.get(name)
        if value in (None, ''):
            return None
        dec = Decimal(str(value))
        if max_abs is not None and (dec < -max_abs or dec > max_abs):
            raise InvalidOperation()
        return dec

    try:
        speed_kmh = optional_decimal('speed_kmh', Decimal('500'))
        accuracy_m = optional_decimal('accuracy_m', Decimal('10000'))
        heading_deg = optional_decimal('heading_deg', Decimal('360'))
    except (InvalidOperation, TypeError, ValueError):
        return JsonResponse({'error': 'Valeurs numériques invalides'}, status=400)

    is_active = bool(payload.get('is_active', True))
    now = timezone.now()

    live_location, created = DriverLiveLocation.objects.get_or_create(
        transport_request=transport_request,
        defaults={
            'driver': transport_request.driver,
            'latitude': latitude,
            'longitude': longitude,
            'speed_kmh': speed_kmh,
            'accuracy_m': accuracy_m,
            'heading_deg': heading_deg,
            'recorded_at': now,
            'is_active': is_active,
            'started_at': now,
            'stopped_at': None if is_active else now,
        },
    )

    if not created:
        if live_location.driver_id != transport_request.driver_id:
            live_location.driver = transport_request.driver
        live_location.latitude = latitude
        live_location.longitude = longitude
        live_location.speed_kmh = speed_kmh
        live_location.accuracy_m = accuracy_m
        live_location.heading_deg = heading_deg
        live_location.recorded_at = now
        live_location.is_active = is_active
        if is_active and live_location.started_at is None:
            live_location.started_at = now
        if not is_active and live_location.stopped_at is None:
            live_location.stopped_at = now
        if is_active:
            live_location.stopped_at = None
        live_location.save()

    return JsonResponse({'ok': True, **_build_live_payload(transport_request)})


@login_required
@role_required('admin', 'secretariat', 'responsable_groupe')
def assign_driver(request, pk):
    """Assigner un chauffeur à une demande de transport."""
    transport_request = get_object_or_404(TransportRequest, pk=pk)
    
    if request.method == 'POST':
        form = DriverAssignmentForm(request.POST, instance=transport_request)
        if form.is_valid():
            transport_request = form.save()
            
            # Si un chauffeur est assigné et le statut est confirmé, envoyer un email
            if transport_request.driver and transport_request.status == 'confirmed':
                try:
                    send_confirmation_email(transport_request)
                    messages.success(request, f'Chauffeur assigné et email de confirmation envoyé à {transport_request.requester_name}.')
                except Exception as e:
                    messages.warning(request, f'Chauffeur assigné mais erreur lors de l\'envoi de l\'email: {str(e)}')
            else:
                messages.success(request, 'Chauffeur assigné avec succès.')
            
            return redirect('transport:request_detail', pk=transport_request.pk)
    else:
        form = DriverAssignmentForm(instance=transport_request)
    
    # Filtrer les chauffeurs disponibles selon la date et les disponibilités
    available_drivers = get_available_drivers_for_request(transport_request)
    form.fields['driver'].queryset = available_drivers
    
    return render(request, 'transport/assign_driver.html', {
        'form': form,
        'transport_request': transport_request,
        'available_drivers': available_drivers
    })


def get_available_drivers_for_request(transport_request):
    """Obtenir les chauffeurs disponibles pour une demande spécifique."""
    from datetime import datetime
    
    # Filtrer par disponibilité générale
    drivers = DriverProfile.objects.filter(is_available=True)
    
    # Filtrer par jour de la semaine
    if transport_request.event_date.weekday() == 6:  # Dimanche
        drivers = drivers.filter(available_sunday=True)
    else:  # Semaine
        drivers = drivers.filter(available_week=True)
    
    # Filtrer par capacité (au moins le nombre de passagers requis)
    drivers = drivers.filter(capacity__gte=transport_request.passengers_count)
    
    # Exclure les chauffeurs déjà assignés à la même heure
    conflicting_requests = TransportRequest.objects.filter(
        event_date=transport_request.event_date,
        event_time=transport_request.event_time,
        status__in=['confirmed', 'pending'],
        driver__isnull=False
    ).exclude(pk=transport_request.pk)
    
    conflicting_driver_ids = conflicting_requests.values_list('driver_id', flat=True)
    drivers = drivers.exclude(id__in=conflicting_driver_ids)
    
    return drivers.select_related('user')


@login_required
@role_required('admin', 'secretariat', 'responsable_groupe')
def transport_calendar(request):
    """Calendrier des transports."""
    return render(request, 'transport/calendar.html')


@login_required
@role_required('admin', 'secretariat', 'responsable_groupe')
def transport_calendar_data(request):
    """API JSON pour les données du calendrier."""
    from datetime import datetime, timedelta
    # Récupérer les paramètres de date
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    if start and end:
        start_date = datetime.fromisoformat(start.replace('Z', '+00:00')).date()
        end_date = datetime.fromisoformat(end.replace('Z', '+00:00')).date()
    else:
        # Par défaut, afficher le mois courant
        today = datetime.now().date()
        start_date = today.replace(day=1)
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    # Récupérer les demandes de transport dans la période
    requests = TransportRequest.objects.filter(
        event_date__gte=start_date,
        event_date__lte=end_date
    ).select_related('driver__user')
    
    events = []
    for req in requests:
        # Couleur selon le statut
        color_map = {
            'pending': '#ffc107',    # warning - jaune
            'confirmed': '#198754',  # success - vert
            'completed': '#0dcaf0',  # info - bleu clair
            'cancelled': '#dc3545',  # danger - rouge
        }
        
        # Titre de l'événement
        title = f"{req.requester_name}"
        if req.driver:
            title += f" → {req.driver.user.get_full_name()}"
        
        # Description pour le tooltip
        description = f"Passagers: {req.passengers_count}"
        if req.event_name:
            description += f"\nÉvénement: {req.event_name}"
        if req.pickup_address:
            description += f"\nAdresse: {req.pickup_address[:50]}..."
        
        events.append({
            'id': req.pk,
            'title': title,
            'start': f"{req.event_date}T{req.event_time}",
            'color': color_map.get(req.status, '#6c757d'),
            'extendedProps': {
                'description': description,
                'status': req.get_status_display(),
                'requester': req.requester_name,
                'driver': req.driver.user.get_full_name() if req.driver else 'Non assigné',
                'passengers': req.passengers_count,
                'phone': req.requester_phone,
                'url': f"/transport/requests/{req.pk}/"
            }
        })
    
    return JsonResponse(events, safe=False)


def send_confirmation_email(transport_request):
    """Envoyer un email de confirmation au demandeur."""
    if not transport_request.driver:
        return
    
    # Vérifier si on a une adresse email
    if not transport_request.requester_email:
        print(f"Pas d'email pour la demande {transport_request.pk} - {transport_request.requester_name}")
        return
    
    subject = f'Confirmation de transport - {transport_request.event_date.strftime("%d/%m/%Y")}'
    
    context = {
        'transport_request': transport_request,
        'driver': transport_request.driver,
    }
    
    # Générer le contenu HTML
    html_message = render_to_string('transport/emails/transport_confirmation.html', context)
    
    # Générer une version texte simple
    text_message = f"""
Bonjour {transport_request.requester_name},

Nous avons le plaisir de vous confirmer qu'un chauffeur a été assigné à votre demande de transport.

Détails du transport:
- Date: {transport_request.event_date.strftime('%d/%m/%Y')}
- Heure: {transport_request.event_time.strftime('%H:%M')}
- Nombre de passagers: {transport_request.passengers_count}
- Adresse de prise en charge: {transport_request.pickup_address}
{f"- Événement: {transport_request.event_name}" if transport_request.event_name else ""}

Votre chauffeur:
- Nom: {transport_request.driver.user.get_full_name()}
- Véhicule: {transport_request.driver.vehicle_type}
{f"- Modèle: {transport_request.driver.vehicle_model}" if transport_request.driver.vehicle_model else ""}
- Capacité: {transport_request.driver.capacity} passagers

Important: Veuillez être prêt(e) à l'heure convenue. Le chauffeur vous contactera si nécessaire.

Si vous avez des questions ou si vous devez modifier votre demande, n'hésitez pas à nous contacter.

Bonne journée,
L'équipe transport de l'EEBC
    """.strip()
    
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@eebc.org')
    
    try:
        send_mail(
            subject=subject,
            message=text_message,
            from_email=from_email,
            recipient_list=[transport_request.requester_email],
            html_message=html_message,
            fail_silently=False
        )
        print(f"Email de confirmation envoyé à {transport_request.requester_email} pour la demande {transport_request.pk}")
        return True
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email pour la demande {transport_request.pk}: {str(e)}")
        raise e


# =============================================================================
# OPÉRATIONS DE SUPPRESSION MANQUANTES - TRANSPORT
# =============================================================================

@login_required
@role_required('admin', 'secretariat', 'responsable_groupe')
def driver_delete(request, pk):
    """Supprimer un profil chauffeur."""
    driver = get_object_or_404(DriverProfile, pk=pk)
    
    # Vérifier s'il y a des demandes de transport liées
    active_requests = driver.transport_requests.filter(
        status__in=['pending', 'confirmed'],
        event_date__gte=date.today()
    )
    
    if request.method == 'POST':
        driver_name = driver.user.get_full_name()
        
        if active_requests.exists():
            # Demander confirmation pour la réassignation
            action = request.POST.get('action')
            if action == 'reassign':
                # Réassigner les demandes à un autre chauffeur
                new_driver_id = request.POST.get('new_driver')
                if new_driver_id:
                    try:
                        new_driver = DriverProfile.objects.get(pk=new_driver_id)
                        active_requests.update(driver=new_driver)
                        messages.success(
                            request, 
                            f'{active_requests.count()} demande(s) réassignée(s) à {new_driver.user.get_full_name()}.'
                        )
                    except DriverProfile.DoesNotExist:
                        messages.error(request, 'Chauffeur de réassignation invalide.')
                        return redirect('transport:driver_delete', pk=pk)
            elif action == 'unassign':
                # Désassigner les demandes (remettre à null)
                active_requests.update(driver=None, status='pending')
                messages.warning(
                    request, 
                    f'{active_requests.count()} demande(s) remise(s) en attente d\'assignation.'
                )
        
        driver.delete()
        messages.success(request, f'Chauffeur "{driver_name}" supprimé avec succès.')
        return redirect('transport:drivers')
    
    # Autres chauffeurs pour réassignation
    other_drivers = DriverProfile.objects.exclude(pk=pk).filter(is_available=True)
    
    context = {
        'driver': driver,
        'active_requests': active_requests,
        'active_requests_count': active_requests.count(),
        'other_drivers': other_drivers,
    }
    return render(request, 'transport/driver_delete_confirm.html', context)


@login_required
@role_required('admin', 'secretariat', 'responsable_groupe')
def transport_request_delete(request, pk):
    """Supprimer une demande de transport."""
    transport_request = get_object_or_404(TransportRequest, pk=pk)
    
    if request.method == 'POST':
        requester_name = transport_request.requester_name
        event_date = transport_request.event_date
        
        # Envoyer un email d'annulation si la demande était confirmée
        if transport_request.status == 'confirmed' and transport_request.requester_email:
            try:
                send_cancellation_email(transport_request)
                messages.info(request, 'Email d\'annulation envoyé au demandeur.')
            except Exception as e:
                messages.warning(request, f'Demande supprimée mais erreur lors de l\'envoi de l\'email: {e}')
        
        transport_request.delete()
        messages.success(request, f'Demande de transport de {requester_name} pour le {event_date.strftime("%d/%m/%Y")} supprimée.')
        return redirect('transport:requests')
    
    context = {
        'transport_request': transport_request,
    }
    return render(request, 'transport/transport_request_delete_confirm.html', context)


def send_cancellation_email(transport_request):
    """Envoyer un email d'annulation au demandeur."""
    subject = f'Annulation de transport - {transport_request.event_date.strftime("%d/%m/%Y")}'
    
    context = {
        'transport_request': transport_request,
    }
    
    # Générer le contenu HTML
    html_message = render_to_string('transport/emails/transport_cancellation.html', context)
    
    # Version texte simple
    text_message = f"""
Bonjour {transport_request.requester_name},

Nous vous informons que votre demande de transport pour le {transport_request.event_date.strftime('%d/%m/%Y')} à {transport_request.event_time.strftime('%H:%M')} a été annulée.

Si vous avez des questions, n'hésitez pas à nous contacter.

Cordialement,
L'équipe transport de l'EEBC
    """.strip()
    
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@eebc.org')
    
    send_mail(
        subject=subject,
        message=text_message,
        from_email=from_email,
        recipient_list=[transport_request.requester_email],
        html_message=html_message,
        fail_silently=False
    )

