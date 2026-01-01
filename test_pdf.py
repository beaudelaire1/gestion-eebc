#!/usr/bin/env python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_eebc.settings')
import django
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model

User = get_user_model()
factory = RequestFactory()

# Test brochure
request = factory.get('/events/calendar/pdf/?mode=brochure&year=2026&month=1')
request.user = User.objects.first()

try:
    from apps.events.views import calendar_pdf
    response = calendar_pdf(request)
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.get('Content-Type')}")
    print(f"Taille: {len(response.content)} bytes")
    
    with open('brochure_calendrier.pdf', 'wb') as f:
        f.write(response.content)
    print("PDF sauvegarde: brochure_calendrier.pdf")
except Exception as e:
    import traceback
    print(f'ERREUR: {e}')
    traceback.print_exc()
