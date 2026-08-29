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
from django.db.models import Q
from datetime import date
from decimal import Decimal, InvalidOperation
import json
import math
from apps.core.permissions import role_required
from apps.members.geocoding import build_canonical_address, geocode_address_with_metadata
from apps.members.models import GeocodedAddress
from .models import DriverProfile, TransportRequest, DriverLiveLocation
from .forms import DriverProfileForm, TransportRequestForm, DriverAssignmentForm
import logging

logger = logging.getLogger(__name__)

DEFAULT_ETA_SPEED_KMH = 25
MIN_LIVE_ETA_SPEED_KMH = 5


def _can_manage_transport_requests(user):
    return user.is_authenticated and (
        user.is_admin or user.has_any_role('admin', 'secretariat', 'responsable_groupe')
    )


def _get_user_driver_profile(user):
    if not user.is_authenticated:
        return None
    try:
        return user.driver_profile
    except DriverProfile.DoesNotExist:
        return None


def _transport_requests_queryset_for_user(user):
    requests_qs = TransportRequest.objects.select_related(
        'driver__user',
        'live_location',
        'requester_member__user',
    ).order_by('-event_date', '-event_time')

    if _can_manage_transport_requests(user):
        return requests_qs

    filters = Q(requester_member__user=user)
    driver_profile = _get_user_driver_profile(user)
    if driver_profile is not None:
        filters |= Q(driver=driver_profile)
        # Un chauffeur peut voir les demandes en attente sans chauffeur pour les accepter.
        filters |= Q(
            driver__isnull=True,
            status=TransportRequest.Status.PENDING,
        )

    return requests_qs.filter(filters).distinct()


def _can_user_accept_request(user, transport_request):
    """Un chauffeur disponible peut accepter une demande en attente sans chauffeur assigné."""
    if not user.is_authenticated:
        return False
    if transport_request.driver_id is not None:
        return False
    if transport_request.status != TransportRequest.Status.PENDING:
        return False
    driver_profile = _get_user_driver_profile(user)
    return bool(driver_profile and driver_profile.is_available)


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
    requests_qs = _transport_requests_queryset_for_user(request.user)
    transport_scope = request.GET.get('scope', '').strip().lower()
    scope_titles = {
        'tracking': ('Suivi chauffeur', 'Demandes confirmées avec chauffeur assigné et accès rapide au suivi live.'),
        'arrivals': ("Arrivées du jour", "Demandes du jour confirmées pour suivre l'arrivée des chauffeurs."),
        'pending': ('Demandes en attente', 'Demandes à traiter ou à assigner côté transport.'),
        'available': ('Demandes disponibles', 'Demandes en attente sans chauffeur, qu’un chauffeur peut accepter.'),
    }

    if transport_scope == 'tracking':
        requests_qs = requests_qs.filter(
            driver__isnull=False,
            status=TransportRequest.Status.CONFIRMED,
        )
    elif transport_scope == 'arrivals':
        requests_qs = requests_qs.filter(
            driver__isnull=False,
            status=TransportRequest.Status.CONFIRMED,
            event_date=timezone.localdate(),
        )
    elif transport_scope == 'pending':
        requests_qs = requests_qs.filter(status=TransportRequest.Status.PENDING)
    elif transport_scope == 'available':
        requests_qs = requests_qs.filter(
            driver__isnull=True,
            status=TransportRequest.Status.PENDING,
        )
    else:
        transport_scope = ''

    paginator = Paginator(requests_qs, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    transport_page_title, transport_page_subtitle = scope_titles.get(
        transport_scope,
        ('Demandes de transport', 'Gestion des demandes de transport'),
    )

    user_driver_profile = _get_user_driver_profile(request.user)

    return render(request, 'transport/transport_requests.html', {
        'requests': page_obj,
        'page_obj': page_obj,
        'can_manage_transport_requests': _can_manage_transport_requests(request.user),
        'is_driver_user': user_driver_profile is not None,
        'transport_scope': transport_scope,
        'transport_page_title': transport_page_title,
        'transport_page_subtitle': transport_page_subtitle,
    })


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
        TransportRequest.objects.select_related('driver__user', 'requester_member__user', 'requester_member__family'), 
        pk=pk
    )

    if not _can_access_live_tracking(request.user, transport_request):
        messages.error(request, "Vous n'avez pas accès à cette demande de transport.")
        return redirect('transport:requests')
    
    can_manage_live_tracking = _can_manage_transport_requests(request.user)
    can_push_live_tracking = bool(
        transport_request.driver
        and (transport_request.driver.user_id == request.user.id or can_manage_live_tracking)
    )
    can_update_pickup_location = _can_update_pickup_location(request.user, transport_request)
    can_accept_request = _can_user_accept_request(request.user, transport_request)
    if transport_request.driver or can_update_pickup_location:
        _get_pickup_location(transport_request, allow_provider=True)

    return render(request, 'transport/transport_request_detail.html', {
        'transport_request': transport_request,
        'can_manage_transport_requests': can_manage_live_tracking,
        'can_assign_driver': can_manage_live_tracking,
        'can_manage_live_tracking': can_manage_live_tracking,
        'can_push_live_tracking': can_push_live_tracking,
        'can_update_pickup_location': can_update_pickup_location,
        'can_accept_request': can_accept_request,
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

    # Un chauffeur peut consulter une demande en attente sans chauffeur pour l'accepter.
    return _can_user_accept_request(user, transport_request)


def _can_update_pickup_location(user, transport_request):
    if not user.is_authenticated:
        return False
    if _can_manage_transport_requests(user):
        return True
    requester_member = transport_request.requester_member
    return bool(requester_member and requester_member.user_id == user.id)


def _pickup_location_from_request_gps(transport_request):
    if transport_request.pickup_latitude is None or transport_request.pickup_longitude is None:
        return None
    if transport_request.pickup_location_source != TransportRequest.PickupLocationSource.REQUESTER_GPS:
        return None
    return {
        'has_location': True,
        'latitude': float(transport_request.pickup_latitude),
        'longitude': float(transport_request.pickup_longitude),
        'address': transport_request.pickup_address,
        'label': transport_request.requester_name,
        'source': 'requester_gps',
        'source_label': 'GPS du demandeur',
        'from_cache': False,
    }


def _pickup_location_from_member(transport_request):
    requester_member = transport_request.requester_member
    if not requester_member:
        return None

    family = requester_member.family
    if family and family.latitude is not None and family.longitude is not None:
        return {
            'has_location': True,
            'latitude': float(family.latitude),
            'longitude': float(family.longitude),
            'source': 'postal_address',
            'source_label': 'Adresse postale',
            'from_cache': True,
        }

    return None


def _resolve_pickup_city_postal(transport_request):
    """Retourne (city, postal_code) en priorisant les champs de la demande."""
    city = (transport_request.pickup_city or '').strip()
    postal_code = (transport_request.pickup_postal_code or '').strip()
    requester_member = transport_request.requester_member
    if not city and requester_member and requester_member.city:
        city = requester_member.city
    if not postal_code and requester_member and requester_member.postal_code:
        postal_code = requester_member.postal_code
    return city, postal_code


def _get_cached_pickup_geocode(transport_request):
    city, postal_code = _resolve_pickup_city_postal(transport_request)
    canonical = build_canonical_address(
        address=transport_request.pickup_address,
        city=city,
        postal_code=postal_code,
    )
    now = timezone.now()
    cache_entry = GeocodedAddress.objects.filter(address_key=canonical['address_key']).first()
    if not cache_entry or (cache_entry.expires_at is not None and cache_entry.expires_at <= now):
        return None
    return {
        'coords': (float(cache_entry.latitude), float(cache_entry.longitude)),
        'address_key': canonical['address_key'],
        'from_cache': True,
        'provider': cache_entry.provider,
    }


def _get_pickup_location(transport_request, allow_provider=False):
    if gps_location := _pickup_location_from_request_gps(transport_request):
        return gps_location

    if member_location := _pickup_location_from_member(transport_request):
        return {
            **member_location,
            'address': transport_request.pickup_address,
            'label': transport_request.requester_name,
        }

    geocode_result = _get_cached_pickup_geocode(transport_request)
    if geocode_result is None and allow_provider:
        city, postal_code = _resolve_pickup_city_postal(transport_request)
        geocode_result = geocode_address_with_metadata(
            address=transport_request.pickup_address,
            city=city,
            postal_code=postal_code,
        )
    if geocode_result is None:
        geocode_result = {
            'coords': None,
            'provider': '',
            'from_cache': False,
        }

    if not (coords := geocode_result.get('coords')):
        return {
            'has_location': False,
            'address': transport_request.pickup_address,
            'label': transport_request.requester_name,
            'source': geocode_result.get('provider') or '',
            'source_label': 'Adresse postale à localiser',
            'from_cache': geocode_result.get('from_cache', False),
        }

    return {
        'has_location': True,
        'latitude': coords[0],
        'longitude': coords[1],
        'address': transport_request.pickup_address,
        'label': transport_request.requester_name,
        'source': 'postal_address',
        'source_label': 'Adresse postale',
        'from_cache': geocode_result.get('from_cache', False),
    }


def _distance_km_between(lat_a, lon_a, lat_b, lon_b):
    earth_radius_km = 6371
    lat_a_rad = math.radians(lat_a)
    lat_b_rad = math.radians(lat_b)
    delta_lat = math.radians(lat_b - lat_a)
    delta_lon = math.radians(lon_b - lon_a)

    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a_rad) * math.cos(lat_b_rad) * math.sin(delta_lon / 2) ** 2
    )
    return earth_radius_km * 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))


def _format_eta_label(eta_minutes):
    return "Moins d'1 min" if eta_minutes <= 1 else f"Environ {eta_minutes} min"


def _build_arrival_payload(live_location, pickup_location):
    if not pickup_location.get('has_location'):
        return {
            'eta_available': False,
            'eta_label': 'Adresse à localiser',
            'eta_minutes': None,
            'eta_mode': 'unavailable',
            'distance_to_pickup_km': None,
            'distance_label': 'Position d\'attente indisponible',
        }

    driver_lat = float(live_location.latitude)
    driver_lng = float(live_location.longitude)
    distance_km = _distance_km_between(
        driver_lat,
        driver_lng,
        pickup_location['latitude'],
        pickup_location['longitude'],
    )

    live_speed = float(live_location.speed_kmh) if live_location.speed_kmh is not None else None
    if live_speed is not None and live_speed >= MIN_LIVE_ETA_SPEED_KMH:
        effective_speed_kmh = live_speed
        eta_mode = 'vitesse_live'
    else:
        effective_speed_kmh = DEFAULT_ETA_SPEED_KMH
        eta_mode = 'moyenne_urbaine'

    eta_minutes = max(1, math.ceil((distance_km / effective_speed_kmh) * 60))
    distance_label = f"{distance_km:.1f} km" if distance_km >= 1 else f"{round(distance_km * 1000)} m"

    return {
        'eta_available': True,
        'eta_label': _format_eta_label(eta_minutes),
        'eta_minutes': eta_minutes,
        'eta_mode': eta_mode,
        'distance_to_pickup_km': round(distance_km, 3),
        'distance_label': distance_label,
    }


def _build_live_payload(transport_request, allow_provider=False):
    live_location = getattr(transport_request, 'live_location', None)
    pickup_location = _get_pickup_location(transport_request, allow_provider=allow_provider)

    if not live_location:
        return {
            'tracking_available': bool(transport_request.driver_id),
            'is_active': False,
            'has_location': False,
            'driver_name': transport_request.driver.user.get_full_name() if transport_request.driver else '',
            'pickup_location': pickup_location,
            'eta_available': False,
            'eta_label': 'En attente du signal GPS',
            'eta_minutes': None,
            'eta_mode': 'waiting_for_driver',
            'distance_to_pickup_km': None,
            'distance_label': 'Position chauffeur indisponible',
        }

    now = timezone.now()
    age_seconds = max(int((now - live_location.recorded_at).total_seconds()), 0)
    arrival_payload = _build_arrival_payload(live_location, pickup_location)

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
        'pickup_location': pickup_location,
        **arrival_payload,
    }


@login_required
@require_GET
def transport_live_status(request, pk):
    """Retourne la position live d'une demande de transport (JSON)."""
    transport_request = get_object_or_404(
        TransportRequest.objects.select_related('driver__user', 'requester_member__user', 'requester_member__family'),
        pk=pk,
    )

    if not _can_access_live_tracking(request.user, transport_request):
        return JsonResponse({'error': 'Accès refusé'}, status=403)

    return JsonResponse(_build_live_payload(transport_request))


@login_required
@require_POST
def transport_pickup_location_update(request, pk):
    """Met à jour la position de prise en charge choisie par le demandeur."""
    transport_request = get_object_or_404(
        TransportRequest.objects.select_related('driver__user', 'requester_member__user', 'requester_member__family'),
        pk=pk,
    )

    if not _can_update_pickup_location(request.user, transport_request):
        return JsonResponse({'error': 'Accès refusé'}, status=403)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalide'}, status=400)

    source = payload.get('source')
    if source == 'gps':
        try:
            latitude = Decimal(str(payload.get('latitude')))
            longitude = Decimal(str(payload.get('longitude')))
        except (InvalidOperation, TypeError, ValueError):
            return JsonResponse({'error': 'Latitude/longitude invalides'}, status=400)

        if latitude < Decimal('-90') or latitude > Decimal('90'):
            return JsonResponse({'error': 'Latitude hors limites'}, status=400)
        if longitude < Decimal('-180') or longitude > Decimal('180'):
            return JsonResponse({'error': 'Longitude hors limites'}, status=400)

        transport_request.pickup_latitude = latitude
        transport_request.pickup_longitude = longitude
        transport_request.pickup_location_source = TransportRequest.PickupLocationSource.REQUESTER_GPS
    elif source == 'address':
        transport_request.pickup_latitude = None
        transport_request.pickup_longitude = None
        transport_request.pickup_location_source = TransportRequest.PickupLocationSource.POSTAL_ADDRESS
    else:
        return JsonResponse({'error': 'Source de position invalide'}, status=400)

    transport_request.pickup_location_updated_at = timezone.now()
    transport_request.save(update_fields=[
        'pickup_latitude',
        'pickup_longitude',
        'pickup_location_source',
        'pickup_location_updated_at',
        'updated_at',
    ])

    return JsonResponse({'ok': True, **_build_live_payload(transport_request, allow_provider=True)})


@login_required
@require_POST
def transport_live_update(request, pk):
    """Met à jour la position GPS live d'un chauffeur (JSON)."""
    transport_request = get_object_or_404(
        TransportRequest.objects.select_related('driver__user', 'requester_member__user', 'requester_member__family'),
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
@require_POST
def transport_request_accept(request, pk):
    """Permet à un chauffeur d'accepter (s'auto-assigner) une demande en attente sans chauffeur."""
    transport_request = get_object_or_404(
        TransportRequest.objects.select_related('driver__user'),
        pk=pk,
    )

    if not _can_user_accept_request(request.user, transport_request):
        messages.error(request, "Cette demande ne peut pas être acceptée.")
        return redirect('transport:request_detail', pk=transport_request.pk)

    driver_profile = _get_user_driver_profile(request.user)
    transport_request.driver = driver_profile
    transport_request.status = TransportRequest.Status.CONFIRMED
    transport_request.save(update_fields=['driver', 'status', 'updated_at'])

    try:
        send_confirmation_email(transport_request)
    except Exception as exc:  # pragma: no cover - notification best-effort
        logger.warning("Email confirmation chauffeur non envoyé: %s", exc)

    messages.success(
        request,
        f"Vous avez accepté la demande de {transport_request.requester_name}.",
    )
    return redirect('transport:request_detail', pk=transport_request.pk)


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


# ===== ACTIONS CHAUFFEUR (SPRINT 1) =====

@login_required
@require_POST
def transport_request_start(request, pk):
    """
    Chauffeur signale qu'il part (CONFIRMED → EN_ROUTE).
    """
    transport_request = get_object_or_404(TransportRequest, pk=pk)
    
    # Vérifications
    if transport_request.status != TransportRequest.Status.CONFIRMED:
        messages.error(request, 'Seules les demandes confirmées peuvent être démarrées.')
        return redirect('transport:request_detail', pk=pk)
    
    if not transport_request.driver or transport_request.driver.user_id != request.user.id:
        messages.error(request, 'Vous devez être le chauffeur assigné.')
        return redirect('transport:requests')
    
    # Transition
    transport_request.status = TransportRequest.Status.EN_ROUTE
    transport_request.save(update_fields=['status', 'updated_at'])
    
    messages.success(request, f'Trajet démarré pour {transport_request.requester_name}.')
    
    # TODO Sprint 2: Envoyer notification passager
    return redirect('transport:request_detail', pk=pk)


@login_required
@require_POST
def transport_request_arriving(request, pk):
    """
    Chauffeur signale qu'il arrive (EN_ROUTE → ARRIVING).
    """
    transport_request = get_object_or_404(TransportRequest, pk=pk)
    
    # Vérifications
    if transport_request.status != TransportRequest.Status.EN_ROUTE:
        messages.error(request, 'Seuls les trajets en route peuvent signaler une arrivée.')
        return redirect('transport:request_detail', pk=pk)
    
    if not transport_request.driver or transport_request.driver.user_id != request.user.id:
        messages.error(request, 'Vous devez être le chauffeur assigné.')
        return redirect('transport:requests')
    
    # Transition
    transport_request.status = TransportRequest.Status.ARRIVING
    transport_request.save(update_fields=['status', 'updated_at'])
    
    messages.success(request, f'Arrivée signalée pour {transport_request.requester_name}.')
    
    # TODO Sprint 2: Envoyer notification passager "j'arrive dans 2 min"
    return redirect('transport:request_detail', pk=pk)


@login_required
@require_POST
def transport_request_complete(request, pk):
    """
    Chauffeur signale que le trajet est effectué (ARRIVING → COMPLETED).
    """
    transport_request = get_object_or_404(TransportRequest, pk=pk)
    
    # Vérifications
    if transport_request.status not in [TransportRequest.Status.ARRIVING, TransportRequest.Status.EN_ROUTE]:
        messages.error(request, 'Seuls les trajets en route ou "en arrivée" peuvent être complétés.')
        return redirect('transport:request_detail', pk=pk)
    
    if not transport_request.driver or transport_request.driver.user_id != request.user.id:
        messages.error(request, 'Vous devez être le chauffeur assigné.')
        return redirect('transport:requests')
    
    # Transition
    transport_request.status = TransportRequest.Status.COMPLETED
    transport_request.save(update_fields=['status', 'updated_at'])
    
    messages.success(request, f'Trajet effectué pour {transport_request.requester_name}.')
    
    # TODO Sprint 2: Envoyer notification passager "trajet complété"
    return redirect('transport:request_detail', pk=pk)

