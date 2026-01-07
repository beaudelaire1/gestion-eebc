"""
Permissions et décorateurs pour le Club Biblique.
Gère l'accès des moniteurs à leurs classes uniquement.
"""
from functools import wraps
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404

from .models import BibleClass, Monitor, Child, Session, Attendance


def get_monitor_for_user(user):
    """Récupère le profil moniteur d'un utilisateur s'il existe."""
    if not user.is_authenticated:
        return None
    try:
        return Monitor.objects.select_related('bible_class').get(user=user, is_active=True)
    except Monitor.DoesNotExist:
        return None


def get_user_classes(user):
    """
    Retourne les classes accessibles par un utilisateur.
    - Admin/Responsable Club : toutes les classes
    - Moniteur : sa classe uniquement
    - Autres : aucune
    """
    if not user.is_authenticated:
        return BibleClass.objects.none()
    
    # Admin ou responsable club : accès total
    if user.is_superuser or user.role in ['admin', 'responsable_club']:
        return BibleClass.objects.filter(is_active=True)
    
    # Moniteur : sa classe uniquement
    monitor = get_monitor_for_user(user)
    if monitor and monitor.bible_class:
        return BibleClass.objects.filter(pk=monitor.bible_class.pk, is_active=True)
    
    return BibleClass.objects.none()


def can_access_class(user, bible_class):
    """Vérifie si un utilisateur peut accéder à une classe."""
    if not user.is_authenticated:
        return False
    
    # Admin ou responsable club : accès total
    if user.is_superuser or user.role in ['admin', 'responsable_club']:
        return True
    
    # Moniteur : sa classe uniquement
    monitor = get_monitor_for_user(user)
    if monitor and monitor.bible_class:
        return monitor.bible_class.pk == bible_class.pk
    
    return False


def can_access_child(user, child):
    """Vérifie si un utilisateur peut accéder à un enfant."""
    if not user.is_authenticated:
        return False
    
    # Admin ou responsable club : accès total
    if user.is_superuser or user.role in ['admin', 'responsable_club']:
        return True
    
    # Moniteur : enfants de sa classe uniquement
    monitor = get_monitor_for_user(user)
    if monitor and monitor.bible_class and child.bible_class:
        return monitor.bible_class.pk == child.bible_class.pk
    
    return False


def can_take_attendance(user, session, bible_class):
    """Vérifie si un utilisateur peut faire l'appel pour une classe."""
    return can_access_class(user, bible_class)


def is_club_staff(user):
    """Vérifie si l'utilisateur fait partie du staff du club biblique."""
    if not user.is_authenticated:
        return False
    
    if user.is_superuser or user.role in ['admin', 'responsable_club', 'moniteur', 'secretariat']:
        return True
    
    monitor = get_monitor_for_user(user)
    return monitor is not None


def is_club_admin(user):
    """Vérifie si l'utilisateur est admin du club biblique."""
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.role in ['admin', 'responsable_club']


# ============================================================================
# DÉCORATEURS
# ============================================================================

def club_staff_required(view_func):
    """Décorateur : accès réservé au staff du club biblique."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_club_staff(request.user):
            messages.error(request, "Accès réservé au personnel du Club Biblique.")
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def club_admin_required(view_func):
    """Décorateur : accès réservé aux admins du club biblique."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_club_admin(request.user):
            messages.error(request, "Accès réservé aux responsables du Club Biblique.")
            return redirect('bibleclub:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def class_access_required(view_func):
    """
    Décorateur : vérifie l'accès à une classe.
    Attend un paramètre 'pk' ou 'class_pk' dans les kwargs.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        class_pk = kwargs.get('pk') or kwargs.get('class_pk')
        if class_pk:
            bible_class = get_object_or_404(BibleClass, pk=class_pk)
            if not can_access_class(request.user, bible_class):
                messages.error(request, "Vous n'avez pas accès à cette classe.")
                return redirect('bibleclub:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def child_access_required(view_func):
    """
    Décorateur : vérifie l'accès à un enfant.
    Attend un paramètre 'pk' dans les kwargs.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        child_pk = kwargs.get('pk')
        if child_pk:
            child = get_object_or_404(Child, pk=child_pk)
            if not can_access_child(request.user, child):
                messages.error(request, "Vous n'avez pas accès à cet enfant.")
                return redirect('bibleclub:children_list')
        return view_func(request, *args, **kwargs)
    return wrapper


def attendance_access_required(view_func):
    """
    Décorateur : vérifie l'accès pour faire l'appel.
    Attend 'session_pk' et 'class_pk' dans les kwargs.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        class_pk = kwargs.get('class_pk')
        if class_pk:
            bible_class = get_object_or_404(BibleClass, pk=class_pk)
            if not can_access_class(request.user, bible_class):
                messages.error(request, "Vous ne pouvez faire l'appel que pour votre classe.")
                return redirect('bibleclub:home')
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================================================
# CONTEXT PROCESSORS
# ============================================================================

def bibleclub_context(request):
    """
    Context processor pour ajouter les infos du club biblique.
    À ajouter dans settings.py TEMPLATES context_processors.
    """
    context = {
        'is_club_staff': False,
        'is_club_admin': False,
        'user_monitor': None,
        'user_class': None,
    }
    
    if request.user.is_authenticated:
        context['is_club_staff'] = is_club_staff(request.user)
        context['is_club_admin'] = is_club_admin(request.user)
        
        monitor = get_monitor_for_user(request.user)
        if monitor:
            context['user_monitor'] = monitor
            context['user_class'] = monitor.bible_class
    
    return context
