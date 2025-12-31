from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import DriverProfile, TransportRequest


@login_required
def driver_list(request):
    """Liste des chauffeurs."""
    drivers = DriverProfile.objects.filter(is_available=True)
    return render(request, 'transport/driver_list.html', {'drivers': drivers})


@login_required
def transport_requests(request):
    """Liste des demandes de transport."""
    requests = TransportRequest.objects.all()
    return render(request, 'transport/transport_requests.html', {'requests': requests})

