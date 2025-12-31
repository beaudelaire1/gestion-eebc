from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from datetime import date, timedelta


@login_required
def home(request):
    """
    Page d'accueil / Tableau de bord principal.
    Vue globale avec stats et accès rapides.
    """
    from apps.members.models import Member
    from apps.bibleclub.models import Child, Session, Attendance, BibleClass
    from apps.events.models import Event
    from apps.campaigns.models import Campaign
    from apps.communication.models import Announcement
    from apps.groups.models import Group
    
    today = date.today()
    
    # Événements à venir (30 prochains jours)
    upcoming_events_count = Event.objects.filter(
        start_date__gte=today,
        start_date__lte=today + timedelta(days=30),
        is_cancelled=False
    ).count()
    
    # Stats globales
    stats = {
        'total_members': Member.objects.filter(status='actif').count(),
        'total_children': Child.objects.filter(is_active=True).count(),
        'total_classes': BibleClass.objects.filter(is_active=True).count(),
        'total_groups': Group.objects.filter(is_active=True).count(),
        'total_events': upcoming_events_count,
    }
    
    # Événements à venir (liste pour affichage)
    upcoming_events = Event.objects.filter(
        start_date__gte=today,
        start_date__lte=today + timedelta(days=14),
        is_cancelled=False
    ).select_related('category').order_by('start_date')[:4]
    
    # Campagnes actives avec alertes
    active_campaigns = Campaign.objects.filter(is_active=True)
    critical_campaigns = [c for c in active_campaigns if c.is_critical]
    
    # Dernière session du club biblique
    last_session = Session.objects.filter(is_cancelled=False).order_by('-date').first()
    session_stats = None
    if last_session:
        attendances = last_session.attendances.all()
        present = attendances.filter(status='present').count()
        late = attendances.filter(status='late').count()
        absent = attendances.filter(status='absent').count()
        total = attendances.count()
        session_stats = {
            'session': last_session,
            'present': present,
            'late': late,
            'absent': absent,
            'total': total,
            'rate': ((present + late) / total * 100) if total > 0 else 0
        }
    
    # Annonces actives
    announcements = Announcement.objects.filter(is_active=True).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=today)
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=today)
    ).order_by('-is_pinned', '-created_at')[:4]
    
    # Notifications non lues
    try:
        unread_notifications = request.user.notifications.filter(is_read=False).count()
    except:
        unread_notifications = 0
    
    # Alertes
    alerts = []
    
    # Alerte campagnes critiques
    for campaign in critical_campaigns[:1]:  # Une seule alerte à la fois
        alerts.append({
            'type': 'warning',
            'icon': 'exclamation-triangle',
            'title': 'Campagne critique',
            'message': f"'{campaign.name}' n'a atteint que {campaign.progress_percentage}% de son objectif. Deadline : {campaign.end_date.strftime('%d/%m/%Y')}",
            'link': f'/campaigns/{campaign.id}/'
        })
    
    context = {
        'stats': stats,
        'upcoming_events': upcoming_events,
        'active_campaigns': active_campaigns[:3],
        'critical_campaigns': critical_campaigns,
        'session_stats': session_stats,
        'announcements': announcements,
        'unread_notifications': unread_notifications,
        'alerts': alerts,
        'today': today,
    }
    
    return render(request, 'dashboard/home.html', context)


@login_required
def quick_stats(request):
    """Stats rapides pour mise à jour HTMX."""
    from apps.members.models import Member
    from apps.bibleclub.models import Child
    
    stats = {
        'total_members': Member.objects.filter(status='actif').count(),
        'total_children': Child.objects.filter(is_active=True).count(),
    }
    
    return render(request, 'dashboard/partials/quick_stats.html', {'stats': stats})
