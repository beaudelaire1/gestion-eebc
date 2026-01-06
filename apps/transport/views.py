from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from apps.core.permissions import role_required
from .models import DriverProfile, TransportRequest
from .forms import DriverProfileForm, TransportRequestForm, DriverAssignmentForm


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
    requests = TransportRequest.objects.select_related('driver__user').order_by('-event_date', '-event_time')
    return render(request, 'transport/transport_requests.html', {'requests': requests})


@login_required
def transport_request_create(request):
    """Créer une nouvelle demande de transport."""
    if request.method == 'POST':
        form = TransportRequestForm(request.POST)
        if form.is_valid():
            transport_request = form.save()
            messages.success(request, 'Demande de transport créée avec succès.')
            return redirect('transport:requests')
    else:
        form = TransportRequestForm()
    
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
        form = TransportRequestForm(request.POST, instance=transport_request)
        if form.is_valid():
            transport_request = form.save()
            messages.success(request, 'Demande de transport mise à jour.')
            return redirect('transport:requests')
    else:
        form = TransportRequestForm(instance=transport_request)
    
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
    
    return render(request, 'transport/transport_request_detail.html', {
        'transport_request': transport_request
    })


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
    from django.http import JsonResponse
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

