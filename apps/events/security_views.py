"""Event views with one visibility policy across HTML, JSON and PDF."""
from __future__ import annotations

import calendar as cal_module
from calendar import monthrange
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from apps.core.security import event_visibility_q, user_has_any_role
from . import views as legacy_views
from .forms import EventSearchForm
from .models import Event, EventCategory, EventRegistration


MONTHS_FR = {
    1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
    5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
    9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre',
}
WEEKDAYS_FR = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']


def _visible_events(user):
    return Event.objects.filter(event_visibility_q(user)).distinct()


def _period_bounds(mode, year, month):
    months_to_show = 3 if mode == 'quarter' else 1
    end_month = month + months_to_show - 1
    end_year = year
    while end_month > 12:
        end_month -= 12
        end_year += 1
    return (
        date(year, month, 1),
        date(end_year, end_month, monthrange(end_year, end_month)[1]),
        months_to_show,
    )


def _build_calendar_context(user, mode, year, month, *, descriptions=False):
    first_day, last_day, months_to_show = _period_bounds(mode, year, month)
    queryset = _visible_events(user).filter(
        start_date__gte=first_day,
        start_date__lte=last_day,
        is_cancelled=False,
    ).select_related('category').order_by('start_date', 'start_time')
    if not descriptions:
        queryset = queryset.only(
            'id', 'title', 'start_date', 'start_time', 'location',
            'category__name', 'category__color',
        )
    all_events = list(queryset)

    events_index = {}
    for event in all_events:
        events_index.setdefault(
            (event.start_date.year, event.start_date.month, event.start_date.day), []
        ).append(event)

    calendars_data = []
    for offset in range(months_to_show):
        current_month = month + offset
        current_year = year
        while current_month > 12:
            current_month -= 12
            current_year += 1
        weeks = []
        for week in cal_module.Calendar(firstweekday=0).monthdayscalendar(current_year, current_month):
            week_data = []
            for day in week:
                week_data.append({
                    'day': day or None,
                    'events': events_index.get((current_year, current_month, day), []) if day else [],
                })
            weeks.append(week_data)
        calendars_data.append({
            'month': current_month,
            'year': current_year,
            'month_name': MONTHS_FR[current_month],
            'weeks': weeks,
        })

    if mode == 'quarter':
        quarter = (month - 1) // 3 + 1
        title = f"Calendrier {quarter}{'er' if quarter == 1 else 'ème'} trimestre {year}"
        step = 3
    else:
        title = f"Calendrier {MONTHS_FR[month]} {year}"
        step = 1

    prev_month = month - step
    prev_year = year
    while prev_month < 1:
        prev_month += 12
        prev_year -= 1
    next_month = month + step
    next_year = year
    while next_month > 12:
        next_month -= 12
        next_year += 1

    return {
        'calendars': calendars_data,
        'jours_semaine': WEEKDAYS_FR,
        'mode': mode,
        'year': year,
        'month': month,
        'title': title,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'all_events': all_events,
    }


@login_required
def calendar_view(request):
    today = date.today()
    visible = _visible_events(request.user)
    upcoming = visible.filter(start_date__gte=today, is_cancelled=False)
    context = {
        'categories': EventCategory.objects.all(),
        'upcoming_count': upcoming.count(),
        'this_month_count': visible.filter(
            start_date__year=today.year,
            start_date__month=today.month,
            is_cancelled=False,
        ).count(),
        'upcoming_events': upcoming.select_related('category').order_by('start_date', 'start_time')[:5],
    }
    return render(request, 'events/calendar.html', context)


@login_required
def events_json(request):
    events = _visible_events(request.user)
    start = request.GET.get('start')
    end = request.GET.get('end')
    if start:
        events = events.filter(start_date__gte=start[:10])
    if end:
        events = events.filter(start_date__lte=end[:10])
    if not user_has_any_role(request.user, 'admin'):
        events = events.filter(is_cancelled=False)

    data = []
    for event in events.select_related('category').prefetch_related('organizers'):
        item = {
            'id': event.id,
            'title': f"[ANNULÉ] {event.title}" if event.is_cancelled else event.title,
            'start': event.start_date.isoformat(),
            'color': '#6c757d' if event.is_cancelled else event.color,
            'allDay': event.all_day,
            'url': f'/app/events/{event.id}/',
            'extendedProps': {
                'location': event.location,
                'description': event.description[:100] + '...' if len(event.description) > 100 else event.description,
                'is_cancelled': event.is_cancelled,
                'visibility': event.visibility,
                'category_name': event.category.name if event.category else None,
                'organizers': [org.get_full_name() or org.username for org in event.organizers.all()],
            },
        }
        if event.start_time and not event.all_day:
            item['start'] = f"{event.start_date.isoformat()}T{event.start_time.isoformat()}"
        if event.end_date:
            if event.end_time and not event.all_day:
                item['end'] = f"{event.end_date.isoformat()}T{event.end_time.isoformat()}"
            else:
                item['end'] = (event.end_date + timedelta(days=1)).isoformat()
        data.append(item)
    return JsonResponse(data, safe=False)


@login_required
def event_list(request):
    today = date.today()
    events = _visible_events(request.user)
    show_past = request.GET.get('show_past', '0') == '1'
    if not show_past:
        events = events.filter(start_date__gte=today)
    if not user_has_any_role(request.user, 'admin'):
        events = events.filter(is_cancelled=False)
    category = request.GET.get('category')
    if category:
        events = events.filter(category_id=category)
    events = events.select_related('category').order_by('start_date', 'start_time')
    page = Paginator(events, 25).get_page(request.GET.get('page', 1))
    return render(request, 'events/event_list.html', {
        'events': page,
        'page_obj': page,
        'categories': EventCategory.objects.all(),
        'show_past': show_past,
    })


@login_required
def event_list_advanced(request):
    form = EventSearchForm(request.GET or None)
    events = _visible_events(request.user).select_related('category').prefetch_related('organizers')
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
        if not form.cleaned_data.get('show_cancelled'):
            events = events.filter(is_cancelled=False)
    else:
        events = events.filter(is_cancelled=False)
    events = events.order_by('start_date', 'start_time').distinct()
    page = Paginator(events, 20).get_page(request.GET.get('page'))
    context = {'form': form, 'events': page, 'total_count': events.count()}
    if request.htmx:
        return render(request, 'events/partials/event_list_content.html', context)
    return render(request, 'events/event_list_advanced.html', context)


@login_required
def event_detail(request, pk):
    event = get_object_or_404(_visible_events(request.user), pk=pk)
    return render(request, 'events/event_detail.html', {
        'event': event,
        'is_registered': event.registrations.filter(user=request.user).exists(),
    })


@login_required
def upcoming_events_partial(request):
    today = date.today()
    events = _visible_events(request.user).filter(
        start_date__gte=today,
        start_date__lte=today + timedelta(days=30),
        is_cancelled=False,
    ).select_related('category').order_by('start_date', 'start_time')[:5]
    return render(request, 'events/partials/upcoming_events.html', {'events': events})


@login_required
def calendar_print(request):
    today = date.today()
    mode = request.GET.get('mode', 'month')
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    context = _build_calendar_context(request.user, mode, year, month)
    context['categories'] = list(EventCategory.objects.only('name', 'color'))
    return render(request, 'events/calendar_print.html', context)


@login_required
def calendar_pdf(request):
    try:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
    except ImportError:
        return calendar_print(request)

    today = date.today()
    mode = request.GET.get('mode', 'month')
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    font_config = FontConfiguration()
    visible = _visible_events(request.user)

    if mode == 'brochure':
        first_day, last_day, _ = _period_bounds('quarter', year, month)
        all_events = list(visible.filter(
            start_date__gte=first_day,
            start_date__lte=last_day,
            is_cancelled=False,
        ).select_related('category').order_by('start_date', 'start_time'))
        context = _build_calendar_context(request.user, 'quarter', year, month, descriptions=True)
        grouped = {}
        for event in all_events:
            key = event.category_id or 0
            grouped.setdefault(key, {
                'name': event.category.name if event.category else 'Autres événements',
                'color': event.category.color if event.category else '#64748b',
                'events': [],
            })['events'].append(event)
        quarter = (month - 1) // 3 + 1
        context.update({
            'title': f"{quarter}{'er' if quarter == 1 else 'ème'} Trimestre {year}",
            'all_events': all_events,
            'events_by_category': sorted(grouped.values(), key=lambda item: len(item['events']), reverse=True),
            'categories': list(EventCategory.objects.only('name', 'color')),
            'total_events': len(all_events),
            'year': year,
        })
        template = 'events/pdf/calendar_brochure.html'
        filename = f'brochure_calendrier_T{quarter}_{year}.pdf'
        css = CSS(string='@page { size: A4 landscape; margin: 0; }', font_config=font_config)
    elif mode == 'week':
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        events = list(visible.filter(
            start_date__gte=week_start,
            start_date__lte=week_end,
            is_cancelled=False,
        ).select_related('category').order_by('start_date', 'start_time'))
        by_date = {}
        for event in events:
            by_date.setdefault(event.start_date, []).append(event)
        context = {
            'mode': 'week',
            'week_days': [
                {'date': week_start + timedelta(days=i), 'name': WEEKDAYS_FR[i], 'events': by_date.get(week_start + timedelta(days=i), [])}
                for i in range(7)
            ],
            'week_start': week_start,
            'week_end': week_end,
            'title': f"Semaine du {week_start.day} au {week_end.day} {MONTHS_FR[week_start.month]} {week_start.year}",
            'categories': list(EventCategory.objects.only('name', 'color')),
        }
        template = 'events/pdf/calendar_week.html'
        filename = f"calendrier_semaine_{week_start.strftime('%Y%m%d')}.pdf"
        css = CSS(string='@page { size: A4 landscape; margin: 8mm; }', font_config=font_config)
    else:
        context = _build_calendar_context(request.user, mode, year, month)
        context['categories'] = list(EventCategory.objects.only('name', 'color'))
        template = 'events/pdf/calendar_month.html'
        filename = (
            f"calendrier_trimestre_{year}_Q{(month - 1) // 3 + 1}.pdf"
            if mode == 'quarter'
            else f"calendrier_{MONTHS_FR[month].lower()}_{year}.pdf"
        )
        css = CSS(string='@page { size: A4 landscape; margin: 6mm; } .calendar-page { page-break-after: always; } .calendar-page:last-child { page-break-after: auto; }', font_config=font_config)

    html = HTML(string=render_to_string(template, context), base_url='.')
    response = HttpResponse(
        html.write_pdf(stylesheets=[css], font_config=font_config),
        content_type='application/pdf',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Cache-Control'] = 'private, no-store'
    return response


@login_required
def event_duplicate(request, pk):
    original = get_object_or_404(_visible_events(request.user), pk=pk)
    if not user_has_any_role(request.user, 'admin') and request.user not in original.organizers.all():
        raise Http404
    return legacy_views.event_duplicate(request, pk)
