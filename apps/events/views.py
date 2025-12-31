from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from datetime import date, timedelta
from calendar import monthrange, month_name
import calendar as cal_module
import json

from .models import Event, EventCategory


@login_required
def calendar_view(request):
    """Vue calendrier avec FullCalendar."""
    categories = EventCategory.objects.all()
    return render(request, 'events/calendar.html', {'categories': categories})


@login_required
def events_json(request):
    """API JSON pour FullCalendar."""
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    events = Event.objects.filter(is_cancelled=False)
    
    if start:
        events = events.filter(start_date__gte=start[:10])
    if end:
        events = events.filter(start_date__lte=end[:10])
    
    # Filtrer par visibilité
    if not request.user.is_authenticated:
        events = events.filter(visibility='public')
    elif not request.user.is_admin:
        events = events.filter(Q(visibility='public') | Q(visibility='members'))
    
    events_data = []
    for event in events:
        event_dict = {
            'id': event.id,
            'title': event.title,
            'start': event.start_date.isoformat(),
            'color': event.color,
            'allDay': event.all_day,
            'url': f'/events/{event.id}/',
        }
        
        if event.start_time:
            event_dict['start'] = f"{event.start_date.isoformat()}T{event.start_time.isoformat()}"
        
        if event.end_date:
            event_dict['end'] = event.end_date.isoformat()
            if event.end_time:
                event_dict['end'] = f"{event.end_date.isoformat()}T{event.end_time.isoformat()}"
        
        events_data.append(event_dict)
    
    return JsonResponse(events_data, safe=False)


@login_required
def event_list(request):
    """Liste des événements à venir."""
    today = date.today()
    events = Event.objects.filter(
        start_date__gte=today,
        is_cancelled=False
    ).select_related('category', 'organizer')
    
    # Filtrer par catégorie
    category = request.GET.get('category')
    if category:
        events = events.filter(category_id=category)
    
    categories = EventCategory.objects.all()
    
    context = {
        'events': events,
        'categories': categories,
    }
    return render(request, 'events/event_list.html', context)


@login_required
def event_detail(request, pk):
    """Détail d'un événement."""
    event = get_object_or_404(Event, pk=pk)
    is_registered = False
    
    if request.user.is_authenticated:
        is_registered = event.registrations.filter(user=request.user).exists()
    
    context = {
        'event': event,
        'is_registered': is_registered,
    }
    return render(request, 'events/event_detail.html', context)


@login_required
def upcoming_events_partial(request):
    """Événements à venir (partiel HTMX)."""
    today = date.today()
    events = Event.objects.filter(
        start_date__gte=today,
        start_date__lte=today + timedelta(days=30),
        is_cancelled=False
    ).select_related('category')[:5]
    
    return render(request, 'events/partials/upcoming_events.html', {'events': events})


@login_required
def calendar_print(request):
    """
    Vue d'impression du calendrier par mois ou trimestre.
    Paramètres GET:
    - mode: 'month' ou 'quarter' (défaut: month)
    - year: année (défaut: année courante)
    - month: mois de départ (défaut: mois courant)
    """
    today = date.today()
    mode = request.GET.get('mode', 'month')
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    # Noms des mois en français
    mois_fr = {
        1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
        5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
        9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
    }
    
    # Jours de la semaine en français
    jours_semaine = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
    
    # Construire les données du calendrier
    calendars_data = []
    
    if mode == 'quarter':
        # Trimestre : 3 mois à partir du mois sélectionné
        months_to_show = 3
    else:
        # Mois unique
        months_to_show = 1
    
    for i in range(months_to_show):
        current_month = month + i
        current_year = year
        
        # Gérer le passage d'année
        while current_month > 12:
            current_month -= 12
            current_year += 1
        
        # Obtenir le calendrier du mois
        cal = cal_module.Calendar(firstweekday=0)  # Lundi = 0
        month_days = cal.monthdayscalendar(current_year, current_month)
        
        # Récupérer les événements du mois
        first_day = date(current_year, current_month, 1)
        last_day = date(current_year, current_month, monthrange(current_year, current_month)[1])
        
        events = Event.objects.filter(
            start_date__gte=first_day,
            start_date__lte=last_day,
            is_cancelled=False
        ).select_related('category').order_by('start_date', 'start_time')
        
        # Organiser les événements par jour
        events_by_day = {}
        for event in events:
            day = event.start_date.day
            if day not in events_by_day:
                events_by_day[day] = []
            events_by_day[day].append(event)
        
        # Construire les semaines avec les événements
        weeks = []
        for week in month_days:
            week_data = []
            for day in week:
                if day == 0:
                    week_data.append({'day': None, 'events': []})
                else:
                    day_events = events_by_day.get(day, [])
                    week_data.append({'day': day, 'events': day_events})
            weeks.append(week_data)
        
        calendars_data.append({
            'month': current_month,
            'year': current_year,
            'month_name': mois_fr[current_month],
            'weeks': weeks,
        })
    
    # Catégories pour la légende
    categories = EventCategory.objects.all()
    
    # Calculer les mois précédent/suivant pour la navigation
    if mode == 'quarter':
        prev_month = month - 3
        next_month = month + 3
    else:
        prev_month = month - 1
        next_month = month + 1
    
    prev_year = year
    next_year = year
    
    while prev_month < 1:
        prev_month += 12
        prev_year -= 1
    while next_month > 12:
        next_month -= 12
        next_year += 1
    
    # Titre du document
    if mode == 'quarter':
        # Déterminer le trimestre
        if month <= 3:
            quarter_name = "1er trimestre"
        elif month <= 6:
            quarter_name = "2ème trimestre"
        elif month <= 9:
            quarter_name = "3ème trimestre"
        else:
            quarter_name = "4ème trimestre"
        title = f"Calendrier {quarter_name} {year}"
    else:
        title = f"Calendrier {mois_fr[month]} {year}"
    
    context = {
        'calendars': calendars_data,
        'categories': categories,
        'jours_semaine': jours_semaine,
        'mode': mode,
        'year': year,
        'month': month,
        'title': title,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
    }
    
    return render(request, 'events/calendar_print.html', context)

