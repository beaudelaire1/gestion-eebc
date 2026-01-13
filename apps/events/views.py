from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.db.models import Q
from django.urls import reverse
from datetime import date, timedelta
from calendar import monthrange
import calendar as cal_module

from apps.core.permissions import role_required
from .models import Event, EventCategory, EventRegistration
from .forms import EventForm, EventCancelForm, EventDuplicateForm, EventSearchForm


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
    
    events = Event.objects.all()
    
    if start:
        events = events.filter(start_date__gte=start[:10])
    if end:
        events = events.filter(start_date__lte=end[:10])
    
    # Filtrer par visibilité
    if not request.user.is_authenticated:
        events = events.filter(visibility='public')
    elif not request.user.is_staff:
        events = events.filter(Q(visibility='public') | Q(visibility='members'))
    
    # Inclure les événements annulés pour les admins/organisateurs
    if not (request.user.role in ['admin', 'secretariat']):
        events = events.filter(is_cancelled=False)
    
    events_data = []
    for event in events.select_related('category').prefetch_related('organizers'):
        event_dict = {
            'id': event.id,
            'title': event.title,
            'start': event.start_date.isoformat(),
            'color': event.color,
            'allDay': event.all_day,
            'url': f'/events/{event.id}/',
            'extendedProps': {
                'location': event.location,
                'description': event.description[:100] + '...' if len(event.description) > 100 else event.description,
                'is_cancelled': event.is_cancelled,
                'visibility': event.visibility,
                'category_name': event.category.name if event.category else None,
                'organizers': [org.get_full_name() or org.username for org in event.organizers.all()],
            }
        }
        
        # Gestion des heures
        if event.start_time and not event.all_day:
            event_dict['start'] = f"{event.start_date.isoformat()}T{event.start_time.isoformat()}"
        
        # Gestion de la date/heure de fin
        if event.end_date:
            if event.end_time and not event.all_day:
                event_dict['end'] = f"{event.end_date.isoformat()}T{event.end_time.isoformat()}"
            else:
                # Pour les événements "toute la journée", ajouter un jour à la date de fin
                # car FullCalendar utilise des dates de fin exclusives
                from datetime import timedelta
                end_date = event.end_date + timedelta(days=1)
                event_dict['end'] = end_date.isoformat()
        
        # Modifier l'apparence des événements annulés
        if event.is_cancelled:
            event_dict['color'] = '#6c757d'  # Gris pour les événements annulés
            event_dict['title'] = f"[ANNULÉ] {event.title}"
        
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


# =============================================================================
# VUES CRUD POUR LES ÉVÉNEMENTS
# =============================================================================

@login_required
@role_required('admin', 'secretariat')
def event_create(request):
    """
    Créer un nouvel événement.
    Requirements: 15.1
    """
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            
            # Ajouter l'utilisateur actuel comme organisateur par défaut
            event.save()
            if not event.organizers.exists():
                event.organizers.add(request.user)
            
            messages.success(request, f"L'événement '{event.title}' a été créé avec succès.")
            return redirect('events:detail', pk=event.pk)
    else:
        # Pré-remplir le formulaire avec les paramètres de l'URL (depuis le calendrier)
        initial_data = {}
        
        # Date de début depuis le calendrier
        if request.GET.get('date'):
            initial_data['start_date'] = request.GET.get('date')
        if request.GET.get('start_date'):
            initial_data['start_date'] = request.GET.get('start_date')
        
        # Date de fin depuis le calendrier (sélection de plage)
        if request.GET.get('end_date'):
            end_date = request.GET.get('end_date')
            # FullCalendar envoie la date de fin exclusive, on soustrait un jour
            from datetime import datetime, timedelta
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                if end_date_obj > datetime.strptime(initial_data.get('start_date', end_date), '%Y-%m-%d').date():
                    initial_data['end_date'] = (end_date_obj - timedelta(days=1)).strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                pass
        
        # Titre pré-rempli
        if request.GET.get('title'):
            initial_data['title'] = request.GET.get('title')
        
        form = EventForm(initial=initial_data)
    
    context = {
        'form': form,
        'title': 'Créer un événement',
        'submit_text': 'Créer l\'événement'
    }
    return render(request, 'events/event_form.html', context)


@login_required
@role_required('admin', 'secretariat')
def event_update(request, pk):
    """
    Modifier un événement existant.
    Requirements: 15.2
    """
    event = get_object_or_404(Event, pk=pk)
    
    # Vérifier si l'utilisateur peut modifier cet événement
    if not request.user.role == 'admin' and request.user not in event.organizers.all():
        messages.error(request, "Vous ne pouvez modifier que les événements que vous organisez.")
        return redirect('events:detail', pk=event.pk)
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            event = form.save()
            messages.success(request, f"L'événement '{event.title}' a été modifié avec succès.")
            return redirect('events:detail', pk=event.pk)
    else:
        form = EventForm(instance=event)
    
    context = {
        'form': form,
        'event': event,
        'title': f'Modifier - {event.title}',
        'submit_text': 'Enregistrer les modifications'
    }
    return render(request, 'events/event_form.html', context)


@login_required
@role_required('admin', 'secretariat')
def event_cancel(request, pk):
    """
    Annuler un événement avec notification aux inscrits.
    Requirements: 15.3
    """
    event = get_object_or_404(Event, pk=pk)
    
    # Vérifier si l'utilisateur peut annuler cet événement
    if not request.user.role == 'admin' and request.user not in event.organizers.all():
        messages.error(request, "Vous ne pouvez annuler que les événements que vous organisez.")
        return redirect('events:detail', pk=event.pk)
    
    if event.is_cancelled:
        messages.warning(request, "Cet événement est déjà annulé.")
        return redirect('events:detail', pk=event.pk)
    
    if request.method == 'POST':
        form = EventCancelForm(request.POST)
        if form.is_valid():
            # Marquer l'événement comme annulé
            event.is_cancelled = True
            event.save()
            
            # Envoyer des notifications si demandé
            if form.cleaned_data['notify_participants']:
                _send_cancellation_notifications(event, form.cleaned_data['reason'])
            
            messages.success(request, f"L'événement '{event.title}' a été annulé.")
            return redirect('events:detail', pk=event.pk)
    else:
        form = EventCancelForm()
    
    # Compter les participants inscrits
    participants_count = event.registrations.count()
    
    context = {
        'form': form,
        'event': event,
        'participants_count': participants_count,
        'title': f'Annuler - {event.title}'
    }
    return render(request, 'events/event_cancel.html', context)


@login_required
@role_required('admin', 'secretariat')
def event_duplicate(request, pk):
    """
    Dupliquer un événement existant.
    Requirements: 15.4
    """
    original_event = get_object_or_404(Event, pk=pk)
    
    if request.method == 'POST':
        form = EventDuplicateForm(request.POST, original_event=original_event)
        if form.is_valid():
            # Créer une copie de l'événement
            new_event = Event.objects.get(pk=original_event.pk)
            new_event.pk = None  # Créer une nouvelle instance
            new_event.id = None
            
            # Modifier les données selon le formulaire
            new_event.title = original_event.title + form.cleaned_data['duplicate_title_suffix']
            new_event.start_date = form.cleaned_data['new_start_date']
            if form.cleaned_data['new_start_time']:
                new_event.start_time = form.cleaned_data['new_start_time']
            
            # Calculer la nouvelle date de fin si elle existait
            if original_event.end_date:
                days_diff = (original_event.end_date - original_event.start_date).days
                new_event.end_date = new_event.start_date + timedelta(days=days_diff)
            
            # Réinitialiser certains champs
            new_event.is_cancelled = False
            new_event.notification_sent = False
            
            new_event.save()
            
            # Copier les organisateurs
            new_event.organizers.set(original_event.organizers.all())
            
            messages.success(request, f"L'événement '{new_event.title}' a été créé par duplication.")
            return redirect('events:detail', pk=new_event.pk)
    else:
        form = EventDuplicateForm(original_event=original_event)
    
    context = {
        'form': form,
        'original_event': original_event,
        'title': f'Dupliquer - {original_event.title}'
    }
    return render(request, 'events/event_duplicate.html', context)


def _send_cancellation_notifications(event, reason):
    """
    Envoie des notifications d'annulation aux participants inscrits.
    """
    # Récupérer tous les participants inscrits
    registrations = EventRegistration.objects.filter(event=event).select_related('user')
    
    if not registrations.exists():
        return
    
    # Préparer le contexte pour l'email
    email_context = {
        'event': event,
        'reason': reason or "Aucune raison spécifiée",
    }
    
    # Envoyer les emails (implémentation basique)
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings
    
    subject = f"Annulation - {event.title}"
    
    for registration in registrations:
        if registration.user.email:
            try:
                # Personnaliser le contexte pour chaque utilisateur
                user_context = email_context.copy()
                user_context['user'] = registration.user
                
                message = render_to_string('events/emails/event_cancelled.html', user_context)
                
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[registration.user.email],
                    fail_silently=True,
                )
            except Exception:
                # En cas d'erreur, continuer avec les autres emails
                continue


@login_required
def event_list_advanced(request):
    """
    Liste avancée des événements avec recherche et filtres.
    """
    form = EventSearchForm(request.GET or None)
    events = Event.objects.select_related('category').prefetch_related('organizers')
    
    # Appliquer les filtres de base
    if not request.user.is_staff:
        # Filtrer par visibilité pour les non-staff
        events = events.filter(Q(visibility='public') | Q(visibility='members'))
    
    # Appliquer les filtres du formulaire
    if form.is_valid():
        search = form.cleaned_data.get('search')
        if search:
            events = events.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(location__icontains=search)
            )
        
        category = form.cleaned_data.get('category')
        if category:
            events = events.filter(category=category)
        
        start_date = form.cleaned_data.get('start_date')
        if start_date:
            events = events.filter(start_date__gte=start_date)
        
        end_date = form.cleaned_data.get('end_date')
        if end_date:
            events = events.filter(start_date__lte=end_date)
        
        visibility = form.cleaned_data.get('visibility')
        if visibility:
            events = events.filter(visibility=visibility)
        
        show_cancelled = form.cleaned_data.get('show_cancelled')
        if not show_cancelled:
            events = events.filter(is_cancelled=False)
    else:
        # Par défaut, ne pas afficher les événements annulés
        events = events.filter(is_cancelled=False)
    
    # Ordonner par date
    events = events.order_by('start_date', 'start_time')
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(events, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'events': page_obj,
        'total_count': events.count(),
    }
    
    if request.htmx:
        return render(request, 'events/partials/event_list_content.html', context)
    return render(request, 'events/event_list_advanced.html', context)


# =============================================================================
# CRUD POUR LES CATÉGORIES D'ÉVÉNEMENTS
# =============================================================================

@login_required
@role_required('admin', 'secretariat')
def category_list(request):
    """Liste des catégories d'événements."""
    categories = EventCategory.objects.all().order_by('name')
    
    # Statistiques d'utilisation
    for category in categories:
        category.events_count = category.events.count()
        category.upcoming_events_count = category.events.filter(
            start_date__gte=date.today(),
            is_cancelled=False
        ).count()
    
    context = {
        'categories': categories,
        'total_categories': categories.count(),
    }
    
    return render(request, 'events/category_list.html', context)


@login_required
@role_required('admin', 'secretariat')
def category_create(request):
    """Créer une nouvelle catégorie d'événement."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        color = request.POST.get('color', '#007bff')
        description = request.POST.get('description', '').strip()
        
        if not name:
            messages.error(request, 'Le nom de la catégorie est requis.')
        else:
            # Vérifier l'unicité
            if EventCategory.objects.filter(name__iexact=name).exists():
                messages.error(request, f'Une catégorie "{name}" existe déjà.')
            else:
                category = EventCategory.objects.create(
                    name=name,
                    color=color,
                    description=description
                )
                messages.success(request, f'Catégorie "{category.name}" créée avec succès.')
                return redirect('events:category_list')
    
    context = {
        'title': 'Nouvelle catégorie',
        'submit_text': 'Créer la catégorie'
    }
    return render(request, 'events/category_form.html', context)


@login_required
@role_required('admin', 'secretariat')
def category_update(request, pk):
    """Modifier une catégorie d'événement."""
    category = get_object_or_404(EventCategory, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        color = request.POST.get('color', '#007bff')
        description = request.POST.get('description', '').strip()
        
        if not name:
            messages.error(request, 'Le nom de la catégorie est requis.')
        else:
            # Vérifier l'unicité (exclure la catégorie actuelle)
            if EventCategory.objects.filter(name__iexact=name).exclude(pk=pk).exists():
                messages.error(request, f'Une catégorie "{name}" existe déjà.')
            else:
                category.name = name
                category.color = color
                category.description = description
                category.save()
                
                messages.success(request, f'Catégorie "{category.name}" modifiée avec succès.')
                return redirect('events:category_list')
    
    context = {
        'category': category,
        'title': f'Modifier {category.name}',
        'submit_text': 'Enregistrer les modifications'
    }
    return render(request, 'events/category_form.html', context)


@login_required
@role_required('admin', 'secretariat')
def category_delete(request, pk):
    """Supprimer une catégorie d'événement."""
    category = get_object_or_404(EventCategory, pk=pk)
    
    # Vérifier s'il y a des événements liés
    events_count = category.events.count()
    
    if request.method == 'POST':
        if events_count > 0:
            # Demander confirmation pour la réassignation
            reassign_to_id = request.POST.get('reassign_to')
            if reassign_to_id:
                try:
                    new_category = EventCategory.objects.get(pk=reassign_to_id)
                    category.events.update(category=new_category)
                    messages.success(
                        request, 
                        f'{events_count} événement(s) réassigné(s) à "{new_category.name}".'
                    )
                except EventCategory.DoesNotExist:
                    messages.error(request, 'Catégorie de réassignation invalide.')
                    return redirect('events:category_delete', pk=pk)
            else:
                # Supprimer la catégorie des événements (mettre à null)
                category.events.update(category=None)
                messages.warning(
                    request, 
                    f'{events_count} événement(s) n\'ont plus de catégorie.'
                )
        
        category_name = category.name
        category.delete()
        messages.success(request, f'Catégorie "{category_name}" supprimée avec succès.')
        return redirect('events:category_list')
    
    # Autres catégories pour réassignation
    other_categories = EventCategory.objects.exclude(pk=pk)
    
    context = {
        'category': category,
        'events_count': events_count,
        'other_categories': other_categories,
    }
    return render(request, 'events/category_delete_confirm.html', context)
