from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.db.models import Q
from datetime import date, timedelta
from calendar import monthrange
import calendar as cal_module

from .models import Event, EventCategory


@login_required
def calendar_view(request):
    """Vue calendrier avec FullCalendar."""
    today = date.today()
    
    # Catégories
    categories = EventCategory.objects.all()
    
    # Stats
    upcoming_count = Event.objects.filter(
        start_date__gte=today,
        is_cancelled=False
    ).count()
    
    this_month_count = Event.objects.filter(
        start_date__year=today.year,
        start_date__month=today.month,
        is_cancelled=False
    ).count()
    
    # Prochains événements
    upcoming_events = Event.objects.filter(
        start_date__gte=today,
        is_cancelled=False
    ).select_related('category').order_by('start_date', 'start_time')[:5]
    
    context = {
        'categories': categories,
        'upcoming_count': upcoming_count,
        'this_month_count': this_month_count,
        'upcoming_events': upcoming_events,
    }
    return render(request, 'events/calendar.html', context)


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
    elif not request.user.is_staff:
        events = events.filter(Q(visibility='public') | Q(visibility='members'))
    
    events_data = []
    for event in events.select_related('category'):
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
    Vue d'impression HTML du calendrier par mois ou trimestre.
    """
    today = date.today()
    mode = request.GET.get('mode', 'month')
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    context = _build_calendar_context(mode, year, month)
    return render(request, 'events/calendar_print.html', context)


@login_required
def calendar_pdf(request):
    """
    Génère un PDF du calendrier avec WeasyPrint.
    Modes: week, month, quarter
    """
    try:
        from weasyprint import HTML, CSS
    except ImportError:
        # Si WeasyPrint n'est pas installé, rediriger vers la vue HTML
        return calendar_print(request)
    
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
    
    jours_semaine = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
    
    if mode == 'week':
        # Semaine courante
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        events = Event.objects.filter(
            start_date__gte=week_start,
            start_date__lte=week_end,
            is_cancelled=False
        ).select_related('category').order_by('start_date', 'start_time')
        
        # Construire les jours de la semaine
        week_days = []
        for i in range(7):
            day_date = week_start + timedelta(days=i)
            day_events = [e for e in events if e.start_date == day_date]
            week_days.append({
                'date': day_date,
                'name': jours_semaine[i],
                'events': day_events,
            })
        
        context = {
            'mode': 'week',
            'week_days': week_days,
            'week_start': week_start,
            'week_end': week_end,
            'title': f"Semaine du {week_start.day} au {week_end.day} {mois_fr[week_start.month]} {year}",
        }
        template = 'events/pdf/calendar_week.html'
    else:
        # Mois ou trimestre
        context = _build_calendar_context(mode, year, month)
        template = 'events/pdf/calendar_month.html'
    
    # Catégories pour la légende
    context['categories'] = EventCategory.objects.all()
    
    # Générer le HTML
    html_string = render_to_string(template, context)
    
    # CSS pour l'impression paysage
    css = CSS(string='''
        @page {
            size: A4 landscape;
            margin: 1cm;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
    ''')
    
    # Générer le PDF
    html = HTML(string=html_string)
    pdf = html.write_pdf(stylesheets=[css])
    
    # Nom du fichier
    if mode == 'week':
        filename = f"calendrier_semaine_{week_start.strftime('%Y%m%d')}.pdf"
    elif mode == 'quarter':
        filename = f"calendrier_trimestre_{year}_Q{(month-1)//3+1}.pdf"
    else:
        filename = f"calendrier_{mois_fr[month].lower()}_{year}.pdf"
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _build_calendar_context(mode, year, month):
    """Construit le contexte pour l'affichage du calendrier."""
    
    mois_fr = {
        1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
        5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
        9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
    }
    
    jours_semaine = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
    
    calendars_data = []
    
    if mode == 'quarter':
        months_to_show = 3
    else:
        months_to_show = 1
    
    for i in range(months_to_show):
        current_month = month + i
        current_year = year
        
        while current_month > 12:
            current_month -= 12
            current_year += 1
        
        cal = cal_module.Calendar(firstweekday=0)
        month_days = cal.monthdayscalendar(current_year, current_month)
        
        first_day = date(current_year, current_month, 1)
        last_day = date(current_year, current_month, monthrange(current_year, current_month)[1])
        
        events = Event.objects.filter(
            start_date__gte=first_day,
            start_date__lte=last_day,
            is_cancelled=False
        ).select_related('category').order_by('start_date', 'start_time')
        
        events_by_day = {}
        for event in events:
            day = event.start_date.day
            if day not in events_by_day:
                events_by_day[day] = []
            events_by_day[day].append(event)
        
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
    
    categories = EventCategory.objects.all()
    
    # Navigation
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
    
    if mode == 'quarter':
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
    
    return {
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
