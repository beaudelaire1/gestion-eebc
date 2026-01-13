from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Q
from django.core.paginator import Paginator
from datetime import date, timedelta, datetime

from .models import AgeGroup, BibleClass, Child, Session, Attendance, Monitor, DriverCheckIn
from .forms import ChildForm, ChildSearchForm
from .permissions import (
    club_staff_required, club_admin_required, class_access_required,
    child_access_required, attendance_access_required,
    get_user_classes, get_monitor_for_user, can_access_class,
    can_access_child, is_club_admin, is_club_staff
)
from .services import OptimizedBibleClubService


@login_required
@club_staff_required
def bibleclub_home(request):
    """Page d'accueil du club biblique."""
    today = date.today()
    user = request.user
    
    # Récupérer les classes accessibles par l'utilisateur
    user_classes = get_user_classes(user)
    monitor = get_monitor_for_user(user)
    
    # Utiliser le service pour les statistiques
    stats = OptimizedBibleClubService.get_dashboard_stats(user)
    
    # Classes avec annotations
    if is_club_admin(user):
        classes = BibleClass.objects.filter(is_active=True).annotate(
            children_count_anno=Count('children', filter=Q(children__is_active=True))
        )
    else:
        if monitor and monitor.bible_class:
            classes = BibleClass.objects.filter(pk=monitor.bible_class.pk).annotate(
                children_count_anno=Count('children', filter=Q(children__is_active=True))
            )
        else:
            classes = BibleClass.objects.none()
    
    # Prochain dimanche
    days_ahead = 6 - today.weekday()  # 6 = dimanche
    if days_ahead <= 0:  # Dimanche déjà passé cette semaine
        days_ahead += 7
    next_sunday = today + timedelta(days_ahead)
    
    # Session du jour si c'est dimanche
    current_session = None
    if today.weekday() == 6:  # Dimanche
        current_session = Session.objects.filter(date=today).first()
    
    # Dernières sessions via le service
    recent_sessions = OptimizedBibleClubService.get_recent_sessions_with_stats(limit=5)
    
    # Données pour le graphique de présences (12 mois)
    attendance_chart_data = OptimizedBibleClubService.get_attendance_chart_data(12)
    
    context = {
        'stats': stats,
        'next_sunday': next_sunday,
        'current_session': current_session,
        'recent_sessions': recent_sessions,
        'classes': classes,
        'monitor': monitor,
        'is_admin': is_club_admin(user),
        'attendance_chart_data': attendance_chart_data,
    }
    return render(request, 'bibleclub/home.html', context)


@login_required
@club_staff_required
def attendance_chart_data(request):
    """
    API endpoint pour les données de graphique de présences.
    
    Requirements: 21.3, 21.4
    """
    months = int(request.GET.get('months', 12))
    
    # Limiter le nombre de mois pour éviter les abus
    if months not in [3, 6, 12, 24]:
        months = 12
    
    # Récupérer les données via le service
    chart_data = OptimizedBibleClubService.get_attendance_chart_data(months)
    
    return JsonResponse(chart_data)


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
    total_count = all_children.count()
    
    # Formulaire de recherche
    search_form = ChildSearchForm(request.GET)
    
    # Filtres
    if search_form.is_valid():
        search = search_form.cleaned_data.get('search')
        bible_class = search_form.cleaned_data.get('bible_class')
        needs_transport = search_form.cleaned_data.get('needs_transport')
        is_active = search_form.cleaned_data.get('is_active')
        
        if search:
            children = children.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(father_name__icontains=search) |
                Q(mother_name__icontains=search)
            )
        
        if bible_class and (is_club_admin(user) or user_classes.filter(pk=bible_class.pk).exists()):
            children = children.filter(bible_class=bible_class)
        
        if needs_transport == 'yes':
            children = children.filter(needs_transport=True)
        elif needs_transport == 'no':
            children = children.filter(needs_transport=False)
        
        if is_active == 'yes':
            children = children.filter(is_active=True)
        elif is_active == 'no':
            children = children.filter(is_active=False)
    
    # Handle direct GET parameters for HTMX requests
    search = request.GET.get('search', '')
    bible_class_id = request.GET.get('bible_class', '')
    
    if search:
        children = children.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(father_name__icontains=search) |
            Q(mother_name__icontains=search)
        )
    
    if bible_class_id and (is_club_admin(user) or user_classes.filter(pk=bible_class_id).exists()):
        children = children.filter(bible_class_id=bible_class_id)
    
    # Pagination
    paginator = Paginator(children, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Classes disponibles pour le filtre
    if is_club_admin(user):
        classes = BibleClass.objects.filter(is_active=True)
    else:
        classes = user_classes
    
    context = {
        'children': page_obj,  # For template compatibility
        'page_obj': page_obj,
        'search_form': search_form,
        'classes': classes,
        'boys_count': boys_count,
        'girls_count': girls_count,
        'transport_count': transport_count,
        'total_count': total_count,
        'is_admin': is_club_admin(user),
        'search': search,
        'selected_bible_class': bible_class_id,
    }
    
    if request.htmx:
        return render(request, 'bibleclub/partials/children_table.html', context)
    return render(request, 'bibleclub/children_list.html', context)


@login_required
@club_staff_required
def child_create(request):
    """Créer un nouvel enfant."""
    if request.method == 'POST':
        form = ChildForm(request.POST, request.FILES)
        if form.is_valid():
            child = form.save()
            messages.success(request, f'Enfant {child.full_name} créé avec succès!')
            return redirect('bibleclub:child_detail', pk=child.pk)
    else:
        form = ChildForm()
    
    context = {
        'form': form,
        'title': 'Ajouter un enfant',
        'submit_text': 'Créer l\'enfant'
    }
    return render(request, 'bibleclub/child_form.html', context)


@login_required
@club_staff_required
@child_access_required
def child_edit(request, pk):
    """Modifier un enfant."""
    child = get_object_or_404(Child, pk=pk)
    
    if request.method == 'POST':
        form = ChildForm(request.POST, request.FILES, instance=child)
        if form.is_valid():
            child = form.save()
            messages.success(request, f'Enfant {child.full_name} modifié avec succès!')
            return redirect('bibleclub:child_detail', pk=child.pk)
    else:
        form = ChildForm(instance=child)
    
    context = {
        'form': form,
        'child': child,
        'title': f'Modifier {child.full_name}',
        'submit_text': 'Enregistrer les modifications'
    }
    return render(request, 'bibleclub/child_form.html', context)


@login_required
@club_staff_required
@child_access_required
def child_delete(request, pk):
    """Supprimer un enfant (désactiver)."""
    child = get_object_or_404(Child, pk=pk)
    
    if request.method == 'POST':
        child.is_active = False
        child.save()
        messages.success(request, f'Enfant {child.full_name} désactivé avec succès!')
        return redirect('bibleclub:children_list')
    
    context = {
        'child': child,
        'title': f'Désactiver {child.full_name}'
    }
    return render(request, 'bibleclub/child_confirm_delete.html', context)


@login_required
@club_staff_required
@child_access_required
def child_detail(request, pk):
    """Détail d'un enfant."""
    child = get_object_or_404(Child, pk=pk)
    
    # Utiliser le service pour les statistiques de présence
    # Simple stats calculation for now
    recent_attendances = child.attendances.select_related('session').order_by('-session__date')[:10]
    total_sessions = child.attendances.count()
    present_count = child.attendances.filter(status='present').count()
    attendance_rate = round((present_count / total_sessions * 100) if total_sessions > 0 else 0, 1)
    
    attendance_stats = {
        'recent_attendances': recent_attendances,
        'attendance_rate': attendance_rate,
        'total_sessions': total_sessions,
        'present_count': present_count
    }
    
    context = {
        'child': child,
        'attendances': attendance_stats['recent_attendances'],
        'attendance_rate': attendance_stats['attendance_rate'],
        'total_sessions': attendance_stats['total_sessions'],
        'present_count': attendance_stats['present_count'],
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
    
    # Initialiser les présences pour la classe
    children = bible_class.children.filter(is_active=True)
    for child in children:
        Attendance.objects.get_or_create(
            session=session,
            child=child,
            defaults={
                'bible_class': bible_class,
                'status': 'absent'
            }
        )
    
    attendances = session.attendances.filter(bible_class=bible_class).select_related('child')
    
    if request.method == 'POST':
        # Collecter les données de présence
        attendance_data = []
        for attendance in attendances:
            status = request.POST.get(f'status_{attendance.id}')
            check_in = request.POST.get(f'checkin_{attendance.id}')
            notes = request.POST.get(f'notes_{attendance.id}', '')
            
            if status:
                attendance_data.append({
                    'child_id': attendance.child_id,
                    'status': status,
                    'check_in_time': check_in if check_in else None,
                    'notes': notes
                })
        
        # Enregistrer les présences
        for data in attendance_data:
            try:
                attendance = Attendance.objects.get(
                    session=session,
                    child_id=data['child_id']
                )
                attendance.status = data['status']
                if data.get('check_in_time'):
                    attendance.check_in_time = datetime.strptime(data['check_in_time'], '%H:%M').time()
                attendance.notes = data.get('notes', '')
                attendance.save()
            except Attendance.DoesNotExist:
                continue
        
        result = {'success': True}
        
        if result.success:
            messages.success(request, f"Appel enregistré pour {bible_class}")
        else:
            messages.error(request, result.error)
        
        # Envoyer notification de fin d'appel aux responsables
        try:
            from apps.communication.email_service import send_session_completed
            from apps.bibleclub.models import Monitor
            
            # Calculer les stats simples
            present_count = session.attendances.filter(bible_class=bible_class, status='present').count()
            total_count = session.attendances.filter(bible_class=bible_class).count()
            stats = {
                'present_count': present_count,
                'total_count': total_count,
                'bible_class': bible_class
            }
            
            # Notifier les moniteurs principaux et admins
            lead_monitors = Monitor.objects.filter(
                Q(is_lead=True) | Q(bible_class=bible_class, is_lead=True)
            ).select_related('user')
            
            for monitor in lead_monitors:
                if monitor.user.email:
                    send_session_completed(
                        session=session,
                        recipient_email=monitor.user.email,
                        recipient_name=monitor.user.get_full_name(),
                        stats=stats
                    )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Erreur notification appel: {e}")
        
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
        # Enregistrer la présence
        attendance.status = status
        attendance.save()
        
        result = {'success': True}
        
        if not result.success:
            return JsonResponse({'error': result.error}, status=400)
        
        # Recharger l'attendance pour avoir les données à jour
        attendance.refresh_from_db()
    
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
            # Créer la session
            session_date_obj = datetime.strptime(session_date, '%Y-%m-%d').date()
            
            session, created = Session.objects.get_or_create(
                date=session_date_obj,
                defaults={'theme': theme}
            )
            
            if created:
                # Auto-créer les présences pour tous les enfants actifs
                children = Child.objects.filter(is_active=True).select_related('bible_class')
                attendances = []
                for child in children:
                    attendances.append(Attendance(
                        session=session,
                        child=child,
                        bible_class=child.bible_class,
                        status='absent'
                    ))
                Attendance.objects.bulk_create(attendances)
                
                result = {
                    'success': True,
                    'data': {
                        'session': session,
                        'created': True
                    }
                }
                messages.success(request, f"Session du {session_date} créée avec succès!")
            else:
                result = {
                    'success': True,
                    'data': {
                        'session': session,
                        'created': False,
                        'message': f"Une session existe déjà pour le {session_date}"
                    }
                }
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


# =============================================================================
# CRUD POUR LES CLASSES BIBLIQUES - OPÉRATIONS MANQUANTES
# =============================================================================

@login_required
@club_admin_required
def bible_class_create(request):
    """Créer une nouvelle classe biblique."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        age_group_id = request.POST.get('age_group')
        description = request.POST.get('description', '').strip()
        max_capacity = request.POST.get('max_capacity')
        
        if not name:
            messages.error(request, 'Le nom de la classe est requis.')
        else:
            # Vérifier l'unicité
            if BibleClass.objects.filter(name__iexact=name, is_active=True).exists():
                messages.error(request, f'Une classe "{name}" existe déjà.')
            else:
                try:
                    age_group = AgeGroup.objects.get(pk=age_group_id) if age_group_id else None
                    
                    bible_class = BibleClass.objects.create(
                        name=name,
                        age_group=age_group,
                        description=description,
                        max_capacity=int(max_capacity) if max_capacity else None,
                        is_active=True
                    )
                    
                    messages.success(request, f'Classe "{bible_class.name}" créée avec succès.')
                    return redirect('bibleclub:class_detail', pk=bible_class.pk)
                except Exception as e:
                    messages.error(request, f'Erreur lors de la création : {e}')
    
    age_groups = AgeGroup.objects.all().order_by('min_age')
    
    context = {
        'age_groups': age_groups,
        'title': 'Nouvelle classe biblique',
        'submit_text': 'Créer la classe'
    }
    return render(request, 'bibleclub/bible_class_form.html', context)


@login_required
@club_admin_required
def bible_class_update(request, pk):
    """Modifier une classe biblique."""
    bible_class = get_object_or_404(BibleClass, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        age_group_id = request.POST.get('age_group')
        description = request.POST.get('description', '').strip()
        max_capacity = request.POST.get('max_capacity')
        is_active = 'is_active' in request.POST
        
        if not name:
            messages.error(request, 'Le nom de la classe est requis.')
        else:
            # Vérifier l'unicité (exclure la classe actuelle)
            if BibleClass.objects.filter(name__iexact=name, is_active=True).exclude(pk=pk).exists():
                messages.error(request, f'Une classe "{name}" existe déjà.')
            else:
                try:
                    age_group = AgeGroup.objects.get(pk=age_group_id) if age_group_id else None
                    
                    bible_class.name = name
                    bible_class.age_group = age_group
                    bible_class.description = description
                    bible_class.max_capacity = int(max_capacity) if max_capacity else None
                    bible_class.is_active = is_active
                    bible_class.save()
                    
                    messages.success(request, f'Classe "{bible_class.name}" modifiée avec succès.')
                    return redirect('bibleclub:class_detail', pk=bible_class.pk)
                except Exception as e:
                    messages.error(request, f'Erreur lors de la modification : {e}')
    
    age_groups = AgeGroup.objects.all().order_by('min_age')
    
    context = {
        'bible_class': bible_class,
        'age_groups': age_groups,
        'title': f'Modifier {bible_class.name}',
        'submit_text': 'Enregistrer les modifications'
    }
    return render(request, 'bibleclub/bible_class_form.html', context)


@login_required
@club_admin_required
def bible_class_delete(request, pk):
    """Supprimer une classe biblique (soft delete)."""
    bible_class = get_object_or_404(BibleClass, pk=pk)
    
    # Vérifier s'il y a des enfants ou moniteurs liés
    children_count = bible_class.children.filter(is_active=True).count()
    monitors_count = bible_class.monitors.filter(is_active=True).count()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'reassign' and (children_count > 0 or monitors_count > 0):
            new_class_id = request.POST.get('new_class')
            if new_class_id:
                try:
                    new_class = BibleClass.objects.get(pk=new_class_id, is_active=True)
                    
                    # Réassigner les enfants
                    if children_count > 0:
                        bible_class.children.filter(is_active=True).update(bible_class=new_class)
                        messages.info(request, f'{children_count} enfant(s) réassigné(s) à "{new_class.name}".')
                    
                    # Réassigner les moniteurs
                    if monitors_count > 0:
                        bible_class.monitors.filter(is_active=True).update(bible_class=new_class)
                        messages.info(request, f'{monitors_count} moniteur(s) réassigné(s) à "{new_class.name}".')
                        
                except BibleClass.DoesNotExist:
                    messages.error(request, 'Classe de réassignation invalide.')
                    return redirect('bibleclub:bible_class_delete', pk=pk)
        
        # Soft delete de la classe
        class_name = bible_class.name
        bible_class.is_active = False
        bible_class.save()
        
        messages.success(request, f'Classe "{class_name}" supprimée avec succès.')
        return redirect('bibleclub:class_list')
    
    # Autres classes pour réassignation
    other_classes = BibleClass.objects.filter(is_active=True).exclude(pk=pk)
    
    context = {
        'bible_class': bible_class,
        'children_count': children_count,
        'monitors_count': monitors_count,
        'other_classes': other_classes,
    }
    return render(request, 'bibleclub/bible_class_delete_confirm.html', context)


# =============================================================================
# CRUD POUR LES MONITEURS - OPÉRATIONS MANQUANTES
# =============================================================================

@login_required
@club_admin_required
def monitor_list(request):
    """Liste des moniteurs."""
    monitors = Monitor.objects.filter(is_active=True).select_related(
        'user', 'bible_class', 'bible_class__age_group'
    ).order_by('user__last_name', 'user__first_name')
    
    # Statistiques
    total_monitors = monitors.count()
    active_monitors = monitors.filter(is_active=True).count()
    monitors_with_class = monitors.exclude(bible_class__isnull=True).count()
    
    context = {
        'monitors': monitors,
        'total_monitors': total_monitors,
        'active_monitors': active_monitors,
        'monitors_with_class': monitors_with_class,
    }
    
    return render(request, 'bibleclub/monitor_list.html', context)


@login_required
@club_admin_required
def monitor_create(request):
    """Créer un nouveau moniteur."""
    if request.method == 'POST':
        user_id = request.POST.get('user')
        bible_class_id = request.POST.get('bible_class')
        role = request.POST.get('role', 'moniteur')
        
        if not user_id:
            messages.error(request, 'Vous devez sélectionner un utilisateur.')
        else:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                
                user = User.objects.get(pk=user_id)
                bible_class = BibleClass.objects.get(pk=bible_class_id) if bible_class_id else None
                
                # Vérifier si l'utilisateur n'est pas déjà moniteur
                if Monitor.objects.filter(user=user, is_active=True).exists():
                    messages.error(request, f'{user.get_full_name()} est déjà moniteur.')
                else:
                    monitor = Monitor.objects.create(
                        user=user,
                        bible_class=bible_class,
                        role=role,
                        is_active=True
                    )
                    
                    messages.success(request, f'Moniteur {user.get_full_name()} créé avec succès.')
                    return redirect('bibleclub:monitor_list')
                    
            except Exception as e:
                messages.error(request, f'Erreur lors de la création : {e}')
    
    # Utilisateurs disponibles (pas encore moniteurs)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    existing_monitor_users = Monitor.objects.filter(is_active=True).values_list('user_id', flat=True)
    available_users = User.objects.filter(is_active=True).exclude(
        id__in=existing_monitor_users
    ).order_by('last_name', 'first_name')
    
    bible_classes = BibleClass.objects.filter(is_active=True).order_by('name')
    
    role_choices = [
        ('moniteur', 'Moniteur'),
        ('assistant', 'Assistant'),
        ('responsable', 'Responsable'),
    ]
    
    context = {
        'available_users': available_users,
        'bible_classes': bible_classes,
        'role_choices': role_choices,
        'title': 'Nouveau moniteur',
        'submit_text': 'Créer le moniteur'
    }
    return render(request, 'bibleclub/monitor_form.html', context)


@login_required
@club_admin_required
def monitor_update(request, pk):
    """Modifier un moniteur."""
    monitor = get_object_or_404(Monitor, pk=pk)
    
    if request.method == 'POST':
        bible_class_id = request.POST.get('bible_class')
        role = request.POST.get('role', 'moniteur')
        is_active = 'is_active' in request.POST
        
        try:
            bible_class = BibleClass.objects.get(pk=bible_class_id) if bible_class_id else None
            
            monitor.bible_class = bible_class
            monitor.role = role
            monitor.is_active = is_active
            monitor.save()
            
            messages.success(request, f'Moniteur {monitor.user.get_full_name()} modifié avec succès.')
            return redirect('bibleclub:monitor_list')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la modification : {e}')
    
    bible_classes = BibleClass.objects.filter(is_active=True).order_by('name')
    
    role_choices = [
        ('moniteur', 'Moniteur'),
        ('assistant', 'Assistant'),
        ('responsable', 'Responsable'),
    ]
    
    context = {
        'monitor': monitor,
        'bible_classes': bible_classes,
        'role_choices': role_choices,
        'title': f'Modifier {monitor.user.get_full_name()}',
        'submit_text': 'Enregistrer les modifications'
    }
    return render(request, 'bibleclub/monitor_form.html', context)


@login_required
@club_admin_required
def monitor_delete(request, pk):
    """Supprimer un moniteur (soft delete)."""
    monitor = get_object_or_404(Monitor, pk=pk)
    
    if request.method == 'POST':
        monitor_name = monitor.user.get_full_name()
        monitor.is_active = False
        monitor.save()
        
        messages.success(request, f'Moniteur {monitor_name} supprimé avec succès.')
        return redirect('bibleclub:monitor_list')
    
    context = {
        'monitor': monitor,
    }
    return render(request, 'bibleclub/monitor_delete_confirm.html', context)
