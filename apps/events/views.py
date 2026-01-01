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
    
    context = _build_calendar_context_optimized(mode, year, month)
    context['categories'] = list(EventCategory.objects.only('name', 'color'))
    return render(request, 'events/calendar_print.html', context)


@login_required
def calendar_pdf(request):
    """
    Génère un PDF du calendrier avec WeasyPrint.
    Modes: week, month, quarter, brochure
    """
    try:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
    except ImportError:
        return calendar_print(request)
    
    today = date.today()
    mode = request.GET.get('mode', 'month')
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    mois_fr = {
        1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
        5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
        9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
    }
    
    jours_semaine = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
    font_config = FontConfiguration()
    
    # Mode brochure = format portrait professionnel avec couverture
    if mode == 'brochure':
        context = _build_calendar_context_optimized('quarter', year, month)
        
        # Récupérer tous les événements pour la liste (avec description)
        months_to_show = 3
        start_month, start_year = month, year
        end_month = month + months_to_show - 1
        end_year = year
        while end_month > 12:
            end_month -= 12
            end_year += 1
        
        first_day = date(start_year, start_month, 1)
        last_day = date(end_year, end_month, monthrange(end_year, end_month)[1])
        
        all_events = list(Event.objects.filter(
            start_date__gte=first_day,
            start_date__lte=last_day,
            is_cancelled=False
        ).select_related('category').order_by('start_date', 'start_time'))
        
        # Regrouper par catégorie avec structure simplifiée pour le template
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
        
        # Convertir en liste triée par nombre d'événements
        events_by_category_list = sorted(
            events_by_category.values(),
            key=lambda x: len(x['events']),
            reverse=True
        )
        
        # Reconstruire le contexte calendrier avec descriptions
        context = _build_calendar_context_with_description('quarter', year, month)
        
        categories = list(EventCategory.objects.only('name', 'color'))
        
        quarter_num = (month - 1) // 3 + 1
        context['title'] = f"{quarter_num}{'er' if quarter_num == 1 else 'ème'} Trimestre {year}"
        context['all_events'] = all_events
        context['events_by_category'] = events_by_category_list
        context['categories'] = categories
        context['total_events'] = len(all_events)
        context['year'] = year
        
        template = 'events/pdf/calendar_brochure.html'
        filename = f"brochure_calendrier_T{quarter_num}_{year}.pdf"
        
        css = CSS(string='''
            @page { size: A4 landscape; margin: 0; }
        ''', font_config=font_config)
    
    elif mode == 'week':
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        events = list(Event.objects.filter(
            start_date__gte=week_start,
            start_date__lte=week_end,
            is_cancelled=False
        ).select_related('category').only(
            'id', 'title', 'start_date', 'start_time', 'location',
            'category__name', 'category__color'
        ).order_by('start_date', 'start_time'))
        
        events_by_date = {}
        for e in events:
            events_by_date.setdefault(e.start_date, []).append(e)
        
        week_days = []
        for i in range(7):
            day_date = week_start + timedelta(days=i)
            week_days.append({
                'date': day_date,
                'name': jours_semaine[i],
                'events': events_by_date.get(day_date, []),
            })
        
        context = {
            'mode': 'week',
            'week_days': week_days,
            'week_start': week_start,
            'week_end': week_end,
            'title': f"Semaine du {week_start.day} au {week_end.day} {mois_fr[week_start.month]} {year}",
            'categories': list(EventCategory.objects.only('name', 'color')),
        }
        template = 'events/pdf/calendar_week.html'
        filename = f"calendrier_semaine_{week_start.strftime('%Y%m%d')}.pdf"
        
        css = CSS(string='''
            @page { size: A4 landscape; margin: 8mm; }
        ''', font_config=font_config)
    
    else:
        context = _build_calendar_context_optimized(mode, year, month)
        context['categories'] = list(EventCategory.objects.only('name', 'color'))
        template = 'events/pdf/calendar_month.html'
        
        if mode == 'quarter':
            filename = f"calendrier_trimestre_{year}_Q{(month-1)//3+1}.pdf"
        else:
            filename = f"calendrier_{mois_fr[month].lower()}_{year}.pdf"
        
        css = CSS(string='''
            @page { size: A4 landscape; margin: 6mm; }
            .calendar-page { page-break-after: always; }
            .calendar-page:last-child { page-break-after: auto; }
        ''', font_config=font_config)
    
    html_string = render_to_string(template, context)
    html = HTML(string=html_string, base_url='.')
    pdf = html.write_pdf(stylesheets=[css], font_config=font_config)
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _build_calendar_context_optimized(mode, year, month):
    """Construit le contexte pour l'affichage du calendrier - VERSION OPTIMISÉE."""
    
    mois_fr = {
        1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
        5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
        9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
    }
    
    jours_semaine = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
    
    months_to_show = 3 if mode == 'quarter' else 1
    
    # Calculer la plage de dates totale
    start_month, start_year = month, year
    end_month = month + months_to_show - 1
    end_year = year
    while end_month > 12:
        end_month -= 12
        end_year += 1
    
    first_day = date(start_year, start_month, 1)
    last_day = date(end_year, end_month, monthrange(end_year, end_month)[1])
    
    # UNE SEULE requête pour tous les événements de la période
    all_events = list(Event.objects.filter(
        start_date__gte=first_day,
        start_date__lte=last_day,
        is_cancelled=False
    ).select_related('category').only(
        'id', 'title', 'start_date', 'start_time', 'location',
        'category__name', 'category__color'
    ).order_by('start_date', 'start_time'))
    
    # Indexer par (année, mois, jour)
    events_index = {}
    for event in all_events:
        key = (event.start_date.year, event.start_date.month, event.start_date.day)
        events_index.setdefault(key, []).append(event)
    
    calendars_data = []
    
    for i in range(months_to_show):
        current_month = month + i
        current_year = year
        while current_month > 12:
            current_month -= 12
            current_year += 1
        
        cal = cal_module.Calendar(firstweekday=0)
        month_days = cal.monthdayscalendar(current_year, current_month)
        
        weeks = []
        for week in month_days:
            week_data = []
            for day in week:
                if day == 0:
                    week_data.append({'day': None, 'events': []})
                else:
                    key = (current_year, current_month, day)
                    week_data.append({'day': day, 'events': events_index.get(key, [])})
            weeks.append(week_data)
        
        calendars_data.append({
            'month': current_month,
            'year': current_year,
            'month_name': mois_fr[current_month],
            'weeks': weeks,
        })
    
    # Navigation
    if mode == 'quarter':
        prev_month, next_month = month - 3, month + 3
        quarter_num = (month - 1) // 3 + 1
        quarter_names = {1: "1er trimestre", 2: "2ème trimestre", 3: "3ème trimestre", 4: "4ème trimestre"}
        title = f"Calendrier {quarter_names[quarter_num]} {year}"
    else:
        prev_month, next_month = month - 1, month + 1
        title = f"Calendrier {mois_fr[month]} {year}"
    
    prev_year, next_year = year, year
    while prev_month < 1:
        prev_month += 12
        prev_year -= 1
    while next_month > 12:
        next_month -= 12
        next_year += 1
    
    return {
        'calendars': calendars_data,
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


def _build_calendar_context_with_description(mode, year, month):
    """Construit le contexte calendrier avec descriptions pour la brochure PDF."""
    
    mois_fr = {
        1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
        5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
        9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
    }
    
    jours_semaine = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
    
    months_to_show = 3 if mode == 'quarter' else 1
    
    start_month, start_year = month, year
    end_month = month + months_to_show - 1
    end_year = year
    while end_month > 12:
        end_month -= 12
        end_year += 1
    
    first_day = date(start_year, start_month, 1)
    last_day = date(end_year, end_month, monthrange(end_year, end_month)[1])
    
    # Charger TOUS les champs y compris description
    all_events = list(Event.objects.filter(
        start_date__gte=first_day,
        start_date__lte=last_day,
        is_cancelled=False
    ).select_related('category').order_by('start_date', 'start_time'))
    
    # Indexer par date
    events_index = {}
    for event in all_events:
        key = (event.start_date.year, event.start_date.month, event.start_date.day)
        events_index.setdefault(key, []).append(event)
    
    calendars_data = []
    
    for i in range(months_to_show):
        current_month = month + i
        current_year = year
        while current_month > 12:
            current_month -= 12
            current_year += 1
        
        cal = cal_module.Calendar(firstweekday=0)
        month_days = cal.monthdayscalendar(current_year, current_month)
        
        weeks = []
        for week in month_days:
            week_data = []
            for day in week:
                if day == 0:
                    week_data.append({'day': None, 'events': []})
                else:
                    key = (current_year, current_month, day)
                    week_data.append({'day': day, 'events': events_index.get(key, [])})
            weeks.append(week_data)
        
        calendars_data.append({
            'month': current_month,
            'year': current_year,
            'month_name': mois_fr[current_month],
            'weeks': weeks,
        })
    
    if mode == 'quarter':
        quarter_num = (month - 1) // 3 + 1
        quarter_names = {1: "1er trimestre", 2: "2ème trimestre", 3: "3ème trimestre", 4: "4ème trimestre"}
        title = f"Calendrier {quarter_names[quarter_num]} {year}"
    else:
        title = f"Calendrier {mois_fr[month]} {year}"
    
    return {
        'calendars': calendars_data,
        'jours_semaine': jours_semaine,
        'mode': mode,
        'year': year,
        'month': month,
        'title': title,
    }
