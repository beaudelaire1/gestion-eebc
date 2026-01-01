#!/usr/bin/env python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_eebc.settings')
import django
django.setup()

from django.template.loader import render_to_string
from apps.events.views import _build_calendar_context_with_description
from apps.events.models import Event, EventCategory
from datetime import date
from calendar import monthrange

year, month = 2026, 1
context = _build_calendar_context_with_description('quarter', year, month)

months_to_show = 3
first_day = date(year, month, 1)
end_month = month + months_to_show - 1
end_year = year
while end_month > 12:
    end_month -= 12
    end_year += 1
last_day = date(end_year, end_month, monthrange(end_year, end_month)[1])

all_events = list(Event.objects.filter(
    start_date__gte=first_day,
    start_date__lte=last_day,
    is_cancelled=False
).select_related('category').order_by('start_date', 'start_time'))

events_by_category = {}
for event in all_events:
    cat_id = event.category_id if event.category else 0
    if cat_id not in events_by_category:
        events_by_category[cat_id] = {
            'name': event.category.name if event.category else 'Autres événements',
            'color': event.category.color if event.category else '#64748b',
            'events': []
        }
    events_by_category[cat_id]['events'].append(event)

events_by_category_list = sorted(events_by_category.values(), key=lambda x: len(x['events']), reverse=True)

quarter_num = (month - 1) // 3 + 1
context['title'] = f"{quarter_num}{'er' if quarter_num == 1 else 'ème'} Trimestre {year}"
context['all_events'] = all_events
context['events_by_category'] = events_by_category_list
context['categories'] = list(EventCategory.objects.only('name', 'color'))
context['total_events'] = len(all_events)
context['year'] = year

html_string = render_to_string('events/pdf/calendar_brochure.html', context)

with open('debug_brochure.html', 'w', encoding='utf-8') as f:
    f.write(html_string)

print("HTML sauvegardé dans debug_brochure.html")
print(f"Nombre de calendriers: {len(context['calendars'])}")
print(f"Nombre de catégories: {len(events_by_category_list)}")
