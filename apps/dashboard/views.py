from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from django.urls import reverse
from datetime import date, timedelta
from apps.dashboard.services import DashboardService


@login_required
def home(request):
    """
    Page d'accueil / Tableau de bord principal (refactored).
    Utilise DashboardService pour extraction de logique et caching.
    """
    from apps.members.models import LifeEvent, VisitationLog
    from apps.campaigns.models import Campaign
    
    today = date.today()
    
    # Q6: Extract stats via service layer with caching
    stats = DashboardService.get_member_stats(request)
    children_classes = DashboardService.get_children_and_classes_stats()
    stats.update({
        'total_children': children_classes['total_children'],
        'total_classes': children_classes['total_classes'],
        'total_groups': DashboardService.get_groups_count(),
        'total_events': DashboardService.get_events_count(),
    })
    
    finance_stats = DashboardService.get_finance_stats()
    pastoral_stats = DashboardService.get_pastoral_stats(request)
    worship_stats = DashboardService.get_worship_stats(request)
    
    # Fetch related data
    recent_life_events = LifeEvent.objects.filter(
        event_date__gte=today - timedelta(days=30)
    ).select_related('primary_member').order_by('-event_date')[:5]
    
    pending_visits = VisitationLog.objects.filter(
        status__in=['planifie', 'a_faire']
    ).select_related('member').order_by('scheduled_date')[:5]
    
    # Get unconfirmed roles for next service
    unconfirmed_roles = []
    if worship_stats['next_service']:
        unconfirmed_roles = list(worship_stats['next_service'].roles.filter(
            status='en_attente'
        ).select_related('member')[:5])
    
    upcoming_events = DashboardService.get_upcoming_events(days=14, limit=4)
    active_campaigns = Campaign.objects.filter(is_active=True)[:3]
    critical_campaigns = [c for c in active_campaigns if c.is_critical]
    session_stats = DashboardService.get_session_stats()
    announcements = DashboardService.get_active_announcements(request)
    
    # Notifications
    try:
        unread_notifications = request.user.notifications.filter(is_read=False).count()
    except:
        unread_notifications = 0
    
    # Build alerts
    alerts = []
    
    if critical_campaigns:
        campaign = critical_campaigns[0]
        alerts.append({
            'type': 'warning',
            'icon': 'exclamation-triangle',
            'title': 'Campagne critique',
            'message': f"'{campaign.name}' n'a atteint que {campaign.progress_percentage}% de son objectif.",
            'link': f'/campaigns/{campaign.id}/'
        })
    
    if pastoral_stats['members_needing_visit'] > 5 and request.user.can_view_member_alerts:
        alerts.append({
            'type': 'info',
            'icon': 'house-heart',
            'title': 'Visites pastorales',
            'message': f"{pastoral_stats['members_needing_visit']} membres n'ont pas été visités depuis plus de 6 mois.",
            'link': reverse('members:members_needing_visit')
        })
    
    if worship_stats['unconfirmed_roles_count'] > 0 and worship_stats['next_service']:
        days_until = (worship_stats['next_service'].event.start_date - today).days
        if days_until <= 3:
            alerts.append({
                'type': 'warning',
                'icon': 'person-exclamation',
                'title': 'Rôles non confirmés',
                'message': f"{worship_stats['unconfirmed_roles_count']} rôle(s) non confirmé(s) pour le culte de dimanche.",
                'link': f'/app/worship/services/{worship_stats["next_service"].pk}/'
            })
    
    context = {
        'stats': stats,
        'finance_stats': finance_stats,
        'pastoral_stats': pastoral_stats,
        'worship_stats': worship_stats,
        'recent_life_events': recent_life_events,
        'pending_visits': pending_visits,
        'unconfirmed_roles': unconfirmed_roles,
        'upcoming_events': upcoming_events,
        'active_campaigns': active_campaigns,
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
