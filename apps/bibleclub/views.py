from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Q
from datetime import date, timedelta

from .models import AgeGroup, BibleClass, Child, Session, Attendance, Monitor, DriverCheckIn
from .permissions import (
    club_staff_required, club_admin_required, class_access_required,
    child_access_required, attendance_access_required,
    get_user_classes, get_monitor_for_user, can_access_class,
    can_access_child, is_club_admin, is_club_staff
)


@login_required
@club_staff_required
def bibleclub_home(request):
    """Page d'accueil du club biblique."""
    today = date.today()
    user = request.user
    
    # Récupérer les classes accessibles par l'utilisateur
    user_classes = get_user_classes(user)
    monitor = get_monitor_for_user(user)
    
    # Statistiques selon le rôle
    if is_club_admin(user):
        # Admin : stats globales
        stats = {
            'total_children': Child.objects.filter(is_active=True).count(),
            'total_classes': BibleClass.objects.filter(is_active=True).count(),
            'total_monitors': Monitor.objects.filter(is_active=True).count(),
        }
        classes = BibleClass.objects.filter(is_active=True).annotate(
            children_count_anno=Count('children', filter=Q(children__is_active=True))
        )
    else:
        # Moniteur : stats de sa classe uniquement
        if monitor and monitor.bible_class:
            my_class = monitor.bible_class
            stats = {
                'total_children': Child.objects.filter(is_active=True, bible_class=my_class).count(),
                'total_classes': 1,
                'total_monitors': Monitor.objects.filter(is_active=True, bible_class=my_class).count(),
            }
            classes = BibleClass.objects.filter(pk=my_class.pk).annotate(
                children_count_anno=Count('children', filter=Q(children__is_active=True))
            )
        else:
            stats = {'total_children': 0, 'total_classes': 0, 'total_monitors': 0}
            classes = BibleClass.objects.none()
    
    # Prochain dimanche
    days_until_sunday = (6 - today.weekday()) % 7
    if days_until_sunday == 0 and today.weekday() != 6:
        days_until_sunday = 7
    next_sunday = today + timedelta(days=days_until_sunday)
    
    # Session du jour si c'est dimanche
    current_session = None
    if today.weekday() == 6:  # Dimanche
        current_session = Session.objects.filter(date=today).first()
    
    # Dernières sessions
    recent_sessions = Session.objects.all()[:5]
    
    context = {
        'stats': stats,
        'next_sunday': next_sunday,
        'current_session': current_session,
        'recent_sessions': recent_sessions,
        'classes': classes,
        'monitor': monitor,
        'is_admin': is_club_admin(user),
    }
    return render(request, 'bibleclub/home.html', context)


@login_required
@club_staff_required
def class_list(request):
    """Liste des classes (filtrée selon les permissions)."""
    user = request.user
    
    if is_club_admin(user):
        classes = BibleClass.objects.filter(is_active=True).select_related('age_group')
    else:
        classes = get_user_classes(user).select_related('age_group')
    
    context = {
        'classes': classes,
        'is_admin': is_club_admin(user),
    }
    return render(request, 'bibleclub/class_list.html', context)


@login_required
@club_staff_required
@class_access_required
def class_detail(request, pk):
    """Détail d'une classe avec ses enfants."""
    bible_class = get_object_or_404(BibleClass, pk=pk)
    children = bible_class.children.filter(is_active=True)
    monitors = bible_class.monitors.filter(is_active=True)
    
    context = {
        'bible_class': bible_class,
        'children': children,
        'monitors': monitors,
        'is_admin': is_club_admin(request.user),
    }
    return render(request, 'bibleclub/class_detail.html', context)


@login_required
@club_staff_required
def children_list(request):
    """Liste des enfants (filtrée selon les permissions)."""
    user = request.user
    user_classes = get_user_classes(user)
    
    # Base queryset selon les permissions
    if is_club_admin(user):
        children = Child.objects.filter(is_active=True).select_related('bible_class', 'bible_class__age_group')
        all_children = Child.objects.filter(is_active=True)
    else:
        children = Child.objects.filter(
            is_active=True, 
            bible_class__in=user_classes
        ).select_related('bible_class', 'bible_class__age_group')
        all_children = children
    
    # Statistiques
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
    
    # Filtre par classe (seulement si l'utilisateur y a accès)
    class_filter = request.GET.get('class')
    selected_class = None
    if class_filter:
        try:
            class_id = int(class_filter)
            if user_classes.filter(pk=class_id).exists():
                children = children.filter(bible_class_id=class_id)
                selected_class = class_id
        except ValueError:
            pass
    
    # Classes disponibles pour le filtre
    classes = user_classes
    
    context = {
        'children': children,
        'classes': classes,
        'search': search,
        'selected_class': selected_class,
        'boys_count': boys_count,
        'girls_count': girls_count,
        'transport_count': transport_count,
        'is_admin': is_club_admin(user),
    }
    
    if request.htmx:
        return render(request, 'bibleclub/partials/children_table.html', context)
    return render(request, 'bibleclub/children_list.html', context)


@login_required
@club_staff_required
@child_access_required
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
        'is_admin': is_club_admin(request.user),
    }
    return render(request, 'bibleclub/child_detail.html', context)


@login_required
@club_staff_required
def session_list(request):
    """Liste des sessions."""
    sessions = Session.objects.annotate(
        present_count=Count('attendances', filter=Q(attendances__status__in=['present', 'late'])),
        total_count=Count('attendances')
    )
    
    context = {
        'sessions': sessions,
        'is_admin': is_club_admin(request.user),
    }
    return render(request, 'bibleclub/session_list.html', context)


@login_required
@club_staff_required
def session_detail(request, pk):
    """Détail d'une session avec appel."""
    session = get_object_or_404(Session, pk=pk)
    user = request.user
    user_classes = get_user_classes(user)
    
    # Grouper les présences par classe (filtrées selon permissions)
    if is_club_admin(user):
        classes = BibleClass.objects.filter(is_active=True)
    else:
        classes = user_classes
    
    attendance_by_class = {}
    for bible_class in classes:
        attendances = session.attendances.filter(bible_class=bible_class).select_related('child')
        attendance_by_class[bible_class] = attendances
    
    context = {
        'session': session,
        'attendance_by_class': attendance_by_class,
        'status_choices': Attendance.Status.choices,
        'is_admin': is_club_admin(user),
        'user_classes': user_classes,
    }
    return render(request, 'bibleclub/session_detail.html', context)


@login_required
@club_staff_required
@attendance_access_required
def take_attendance(request, session_pk, class_pk):
    """Faire l'appel pour une classe."""
    session = get_object_or_404(Session, pk=session_pk)
    bible_class = get_object_or_404(BibleClass, pk=class_pk)
    
    # Vérification supplémentaire des permissions
    if not can_access_class(request.user, bible_class):
        messages.error(request, "Vous ne pouvez faire l'appel que pour votre classe.")
        return redirect('bibleclub:session_detail', pk=session_pk)
    
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
@club_staff_required
def update_attendance_status(request, attendance_pk):
    """Mise à jour rapide du statut de présence (HTMX)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    attendance = get_object_or_404(Attendance, pk=attendance_pk)
    
    # Vérifier les permissions sur la classe
    if attendance.bible_class and not can_access_class(request.user, attendance.bible_class):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
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
@club_admin_required
def create_session(request):
    """Créer une nouvelle session (admin seulement)."""
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
@club_staff_required
def transport_checkin(request, session_pk):
    """Pointage des chauffeurs pour une session."""
    session = get_object_or_404(Session, pk=session_pk)
    checkins = session.driver_checkins.all().select_related('driver', 'driver__user')
    
    context = {
        'session': session,
        'checkins': checkins,
        'is_admin': is_club_admin(request.user),
    }
    return render(request, 'bibleclub/transport_checkin.html', context)


# ============================================================================
# API pour HTMX
# ============================================================================

@login_required
@club_staff_required
def my_class_children(request):
    """Retourne les enfants de la classe du moniteur connecté (HTMX)."""
    monitor = get_monitor_for_user(request.user)
    
    if not monitor or not monitor.bible_class:
        return render(request, 'bibleclub/partials/no_class.html')
    
    children = Child.objects.filter(
        is_active=True,
        bible_class=monitor.bible_class
    ).order_by('last_name', 'first_name')
    
    return render(request, 'bibleclub/partials/children_table.html', {
        'children': children,
        'bible_class': monitor.bible_class,
    })
