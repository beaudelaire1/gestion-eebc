from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Q
from datetime import date, timedelta

from .models import AgeGroup, BibleClass, Child, Session, Attendance, Monitor, DriverCheckIn


@login_required
def bibleclub_home(request):
    """Page d'accueil du club biblique."""
    today = date.today()
    
    # Statistiques
    stats = {
        'total_children': Child.objects.filter(is_active=True).count(),
        'total_classes': BibleClass.objects.filter(is_active=True).count(),
        'total_monitors': Monitor.objects.filter(is_active=True).count(),
    }
    
    # Prochaine session (dimanche)
    next_sunday = today + timedelta(days=(6 - today.weekday()) % 7)
    if next_sunday == today and today.weekday() != 6:
        next_sunday += timedelta(days=7)
    
    # Session du jour si c'est dimanche
    current_session = None
    if today.weekday() == 6:  # Dimanche
        current_session = Session.objects.filter(date=today).first()
    
    # Dernières sessions
    recent_sessions = Session.objects.all()[:5]
    
    # Classes avec statistiques
    classes = BibleClass.objects.filter(is_active=True).annotate(
        children_count_anno=Count('children', filter=Q(children__is_active=True))
    )
    
    context = {
        'stats': stats,
        'next_sunday': next_sunday,
        'current_session': current_session,
        'recent_sessions': recent_sessions,
        'classes': classes,
    }
    return render(request, 'bibleclub/home.html', context)


@login_required
def class_list(request):
    """Liste des classes."""
    classes = BibleClass.objects.filter(is_active=True).select_related('age_group')
    return render(request, 'bibleclub/class_list.html', {'classes': classes})


@login_required
def class_detail(request, pk):
    """Détail d'une classe avec ses enfants."""
    bible_class = get_object_or_404(BibleClass, pk=pk)
    children = bible_class.children.filter(is_active=True)
    monitors = bible_class.monitors.filter(is_active=True)
    
    context = {
        'bible_class': bible_class,
        'children': children,
        'monitors': monitors,
    }
    return render(request, 'bibleclub/class_detail.html', context)


@login_required
def children_list(request):
    """Liste de tous les enfants."""
    children = Child.objects.filter(is_active=True).select_related('bible_class', 'bible_class__age_group')
    
    # Statistiques globales (avant filtrage)
    all_children = Child.objects.filter(is_active=True)
    boys_count = all_children.filter(gender='M').count()
    girls_count = all_children.filter(gender='F').count()
    transport_count = all_children.filter(needs_transport=True).count()
    
    # Recherche
    search = request.GET.get('search', '')
    if search:
        children = children.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(parent1_name__icontains=search)
        )
    
    # Filtre par classe
    class_filter = request.GET.get('class')
    selected_class = None
    if class_filter:
        children = children.filter(bible_class_id=class_filter)
        try:
            selected_class = int(class_filter)
        except ValueError:
            pass
    
    classes = BibleClass.objects.filter(is_active=True)
    
    context = {
        'children': children,
        'classes': classes,
        'search': search,
        'selected_class': selected_class,
        'boys_count': boys_count,
        'girls_count': girls_count,
        'transport_count': transport_count,
    }
    
    if request.htmx:
        return render(request, 'bibleclub/partials/children_table.html', context)
    return render(request, 'bibleclub/children_list.html', context)


@login_required
def child_detail(request, pk):
    """Détail d'un enfant."""
    child = get_object_or_404(Child, pk=pk)
    attendances = child.attendances.select_related('session').order_by('-session__date')[:10]
    
    # Stats de présence
    total_sessions = child.attendances.count()
    present_count = child.attendances.filter(status__in=['present', 'late']).count()
    attendance_rate = (present_count / total_sessions * 100) if total_sessions > 0 else 0
    
    context = {
        'child': child,
        'attendances': attendances,
        'attendance_rate': attendance_rate,
        'total_sessions': total_sessions,
        'present_count': present_count,
    }
    return render(request, 'bibleclub/child_detail.html', context)


@login_required
def session_list(request):
    """Liste des sessions."""
    sessions = Session.objects.annotate(
        present_count=Count('attendances', filter=Q(attendances__status__in=['present', 'late'])),
        total_count=Count('attendances')
    )
    return render(request, 'bibleclub/session_list.html', {'sessions': sessions})


@login_required
def session_detail(request, pk):
    """Détail d'une session avec appel."""
    session = get_object_or_404(Session, pk=pk)
    
    # Grouper les présences par classe
    classes = BibleClass.objects.filter(is_active=True).prefetch_related(
        'children'
    )
    
    attendance_by_class = {}
    for bible_class in classes:
        attendances = session.attendances.filter(bible_class=bible_class).select_related('child')
        attendance_by_class[bible_class] = attendances
    
    context = {
        'session': session,
        'attendance_by_class': attendance_by_class,
        'status_choices': Attendance.Status.choices,
    }
    return render(request, 'bibleclub/session_detail.html', context)


@login_required
def take_attendance(request, session_pk, class_pk):
    """Faire l'appel pour une classe."""
    session = get_object_or_404(Session, pk=session_pk)
    bible_class = get_object_or_404(BibleClass, pk=class_pk)
    
    # Récupérer ou créer les présences pour tous les enfants de la classe
    children = bible_class.children.filter(is_active=True)
    
    for child in children:
        Attendance.objects.get_or_create(
            session=session,
            child=child,
            defaults={'bible_class': bible_class, 'status': Attendance.Status.ABSENT}
        )
    
    attendances = session.attendances.filter(bible_class=bible_class).select_related('child')
    
    if request.method == 'POST':
        for attendance in attendances:
            status = request.POST.get(f'status_{attendance.id}')
            check_in = request.POST.get(f'checkin_{attendance.id}')
            notes = request.POST.get(f'notes_{attendance.id}', '')
            
            if status:
                attendance.status = status
                attendance.notes = notes
                if check_in:
                    attendance.check_in_time = check_in
                if status in ['present', 'late'] and not attendance.check_in_time:
                    attendance.check_in_time = timezone.now().time()
                attendance.recorded_by = request.user
                attendance.save()
        
        messages.success(request, f"Appel enregistré pour {bible_class}")
        
        if request.htmx:
            return render(request, 'bibleclub/partials/attendance_saved.html', {
                'bible_class': bible_class,
                'session': session
            })
        return redirect('bibleclub:session_detail', pk=session_pk)
    
    context = {
        'session': session,
        'bible_class': bible_class,
        'attendances': attendances,
        'status_choices': Attendance.Status.choices,
    }
    return render(request, 'bibleclub/take_attendance.html', context)


@login_required
def update_attendance_status(request, attendance_pk):
    """Mise à jour rapide du statut de présence (HTMX)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    attendance = get_object_or_404(Attendance, pk=attendance_pk)
    status = request.POST.get('status')
    
    if status and status in dict(Attendance.Status.choices):
        attendance.status = status
        if status in ['present', 'late'] and not attendance.check_in_time:
            attendance.check_in_time = timezone.now().time()
        attendance.recorded_by = request.user
        attendance.save()
    
    return render(request, 'bibleclub/partials/attendance_row.html', {
        'attendance': attendance,
        'status_choices': Attendance.Status.choices,
    })


@login_required
def create_session(request):
    """Créer une nouvelle session."""
    if request.method == 'POST':
        session_date = request.POST.get('date')
        theme = request.POST.get('theme', '')
        
        if session_date:
            session, created = Session.objects.get_or_create(
                date=session_date,
                defaults={'theme': theme}
            )
            
            if created:
                # Créer automatiquement les présences pour tous les enfants actifs
                for child in Child.objects.filter(is_active=True):
                    Attendance.objects.create(
                        session=session,
                        child=child,
                        bible_class=child.bible_class,
                        status=Attendance.Status.ABSENT
                    )
                messages.success(request, f"Session du {session_date} créée avec succès!")
            else:
                messages.info(request, f"Une session existe déjà pour le {session_date}")
            
            return redirect('bibleclub:session_detail', pk=session.pk)
    
    return render(request, 'bibleclub/create_session.html')


@login_required
def transport_checkin(request, session_pk):
    """Pointage des chauffeurs pour une session."""
    session = get_object_or_404(Session, pk=session_pk)
    checkins = session.driver_checkins.all().select_related('driver', 'driver__user')
    
    context = {
        'session': session,
        'checkins': checkins,
    }
    return render(request, 'bibleclub/transport_checkin.html', context)

