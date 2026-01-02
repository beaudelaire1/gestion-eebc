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
    from apps.members.models import Member, LifeEvent, VisitationLog
    from apps.bibleclub.models import Child, Session, Attendance, BibleClass
    from apps.events.models import Event
    from apps.campaigns.models import Campaign
    from apps.communication.models import Announcement
    from apps.groups.models import Group
    from apps.finance.models import FinancialTransaction
    from apps.worship.models import WorshipService, ServiceRole
    
    today = date.today()
    start_of_month = today.replace(day=1)
    
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
    
    # ========== STATS FINANCE ==========
    month_transactions = FinancialTransaction.objects.filter(
        transaction_date__gte=start_of_month,
        status='valide'
    )
    finance_stats = {
        'month_income': month_transactions.filter(
            transaction_type__in=['don', 'dime', 'offrande']
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'month_expenses': month_transactions.filter(
            transaction_type='depense'
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'pending_transactions': FinancialTransaction.objects.filter(
            status='en_attente'
        ).count(),
    }
    finance_stats['month_balance'] = finance_stats['month_income'] - finance_stats['month_expenses']
    
    # ========== STATS PASTORAL CRM ==========
    # Membres nécessitant une visite (pas visités depuis 6 mois)
    members_needing_visit = []
    for member in Member.objects.filter(status='actif')[:100]:  # Limiter pour perf
        if member.needs_visit:
            members_needing_visit.append(member)
    
    # Événements de vie récents (30 derniers jours)
    recent_life_events = LifeEvent.objects.filter(
        event_date__gte=today - timedelta(days=30)
    ).select_related('primary_member').order_by('-event_date')[:5]
    
    # Visites à faire
    pending_visits = VisitationLog.objects.filter(
        status__in=['planifie', 'a_faire']
    ).select_related('member').order_by('scheduled_date')[:5]
    
    pastoral_stats = {
        'members_needing_visit': len(members_needing_visit[:10]),
        'recent_life_events_count': recent_life_events.count(),
        'pending_visits_count': pending_visits.count(),
    }
    
    # ========== STATS WORSHIP ==========
    # Prochain culte
    next_service = WorshipService.objects.filter(
        event__start_date__gte=today
    ).select_related('event').order_by('event__start_date').first()
    
    # Rôles non confirmés pour le prochain culte
    unconfirmed_roles = []
    if next_service:
        unconfirmed_roles = next_service.roles.filter(
            status='en_attente'
        ).select_related('member')[:5]
    
    worship_stats = {
        'next_service': next_service,
        'unconfirmed_roles_count': len(unconfirmed_roles),
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
    for campaign in critical_campaigns[:1]:
        alerts.append({
            'type': 'warning',
            'icon': 'exclamation-triangle',
            'title': 'Campagne critique',
            'message': f"'{campaign.name}' n'a atteint que {campaign.progress_percentage}% de son objectif.",
            'link': f'/campaigns/{campaign.id}/'
        })
    
    # Alerte visites pastorales
    if pastoral_stats['members_needing_visit'] > 5:
        alerts.append({
            'type': 'info',
            'icon': 'house-heart',
            'title': 'Visites pastorales',
            'message': f"{pastoral_stats['members_needing_visit']} membres n'ont pas été visités depuis plus de 6 mois.",
            'link': '/admin/members/visitationlog/'
        })
    
    # Alerte rôles non confirmés
    if worship_stats['unconfirmed_roles_count'] > 0 and next_service:
        days_until = (next_service.event.start_date - today).days
        if days_until <= 3:
            alerts.append({
                'type': 'warning',
                'icon': 'person-exclamation',
                'title': 'Rôles non confirmés',
                'message': f"{worship_stats['unconfirmed_roles_count']} rôle(s) non confirmé(s) pour le culte de dimanche.",
                'link': f'/app/worship/services/{next_service.pk}/'
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
