#!/usr/bin/env python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_eebc.settings')
import django
django.setup()

from apps.events.models import Event, EventCategory
from datetime import date

events = Event.objects.filter(
    start_date__gte=date(2026, 1, 1),
    start_date__lte=date(2026, 3, 31),
    is_cancelled=False
).select_related('category')

print(f"Événements T1 2026: {events.count()}")

cats = EventCategory.objects.all()
print(f"Catégories: {cats.count()}")
for c in cats:
    print(f"  - {c.name}: {c.color}")

print("\nÉvénements:")
for e in events[:15]:
    cat_name = e.category.name if e.category else "Sans catégorie"
    print(f"  {e.start_date} - {e.title} ({cat_name})")
