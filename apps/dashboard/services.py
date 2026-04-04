"""
Dashboard Service - Extracted statistics and data gathering for dashboard views.
Separates business logic from view logic for better maintainability and caching.
"""

from django.core.cache import cache
from django.db.models import Count, Sum, Q
from datetime import date, timedelta
from typing import Dict, List, Optional


class DashboardService:
    """Service for dashboard statistics and data gathering."""
    
    CACHE_TIMEOUT = 600  # 10 minutes
    
    @staticmethod
    def get_member_stats(request) -> Dict:
        """Get member statistics with select_related to avoid N+1 queries."""
        cache_key = f'dashboard_member_stats_{request.user.site_id}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        from apps.members.models import Member
        
        members_qs = Member.objects.all()
        members_by_status = {
            s['status']: s['n']
            for s in members_qs.values('status').annotate(n=Count('id'))
        }
        
        stats = {
            'total_members': members_qs.count(),
            'members_actif': members_by_status.get('actif', 0),
            'members_visiteur': members_by_status.get('visiteur', 0),
            'members_inactif': members_by_status.get('inactif', 0),
            'members_transfere': members_by_status.get('transfere', 0),
        }
        
        cache.set(cache_key, stats, DashboardService.CACHE_TIMEOUT)
        return stats
    
    @staticmethod
    def get_children_and_classes_stats() -> Dict:
        """Get Bible club statistics."""
        cache_key = 'dashboard_children_classes_stats'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        from apps.bibleclub.models import Child, BibleClass
        
        stats = {
            'total_children': Child.objects.filter(is_active=True).count(),
            'total_classes': BibleClass.objects.filter(is_active=True).count(),
        }
        
        cache.set(cache_key, stats, DashboardService.CACHE_TIMEOUT)
        return stats
    
    @staticmethod
    def get_finance_stats() -> Dict:
        """Get finance statistics caching for performance."""
        cache_key = 'dashboard_finance_stats'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        from apps.finance.models import FinancialTransaction
        
        today = date.today()
        start_of_month = today.replace(day=1)
        
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
        
        cache.set(cache_key, finance_stats, DashboardService.CACHE_TIMEOUT)
        return finance_stats
    
    @staticmethod
    def get_pastoral_stats(request) -> Dict:
        """Get pastoral care statistics."""
        cache_key = f'dashboard_pastoral_stats_{request.user.site_id}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        from apps.members.models import Member, LifeEvent, VisitationLog
        
        today = date.today()
        
        # Members needing visit (use select_related to avoid N+1)
        members_needing_visit_qs = Member.objects.filter(
            status='actif'
        ).select_related('site').filter(
            Q(last_visited__isnull=True) | Q(last_visited__lte=today - timedelta(days=180))
        )
        
        pastoral_stats = {
            'members_needing_visit': min(members_needing_visit_qs.count(), 10),
            'recent_life_events_count': LifeEvent.objects.filter(
                event_date__gte=today - timedelta(days=30)
            ).count(),
            'pending_visits_count': VisitationLog.objects.filter(
                status__in=['planifie', 'a_faire']
            ).count(),
        }
        
        cache.set(cache_key, pastoral_stats, DashboardService.CACHE_TIMEOUT)
        return pastoral_stats
    
    @staticmethod
    def get_upcoming_events(days: int = 30, limit: int = 4) -> List:
        """Get upcoming events."""
        cache_key = f'dashboard_upcoming_events_{days}_{limit}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        from apps.events.models import Event
        
        today = date.today()
        events = Event.objects.filter(
            start_date__gte=today,
            start_date__lte=today + timedelta(days=days),
            is_cancelled=False
        ).select_related('category').order_by('start_date')[:limit]
        
        cache.set(cache_key, list(events), DashboardService.CACHE_TIMEOUT)
        return events
    
    @staticmethod
    def get_worship_stats(request) -> Dict:
        """Get worship service statistics."""
        from apps.worship.models import WorshipService
        
        today = date.today()
        next_service = WorshipService.objects.filter(
            event__start_date__gte=today
        ).select_related('event').order_by('event__start_date').first()
        
        unconfirmed_roles_count = 0
        if next_service:
            unconfirmed_roles_count = next_service.roles.filter(
                status='en_attente'
            ).count()
        
        return {
            'next_service': next_service,
            'unconfirmed_roles_count': unconfirmed_roles_count,
        }
    
    @staticmethod
    def get_session_stats() -> Optional[Dict]:
        """Get latest Bible club session statistics."""
        from apps.bibleclub.models import Session
        
        last_session = Session.objects.filter(
            is_cancelled=False
        ).select_related('bible_class').order_by('-date').first()
        
        if not last_session:
            return None
        
        attendances = last_session.attendances.all()
        present = attendances.filter(status='present').count()
        late = attendances.filter(status='late').count()
        absent = attendances.filter(status='absent').count()
        total = attendances.count()
        
        return {
            'session': last_session,
            'present': present,
            'late': late,
            'absent': absent,
            'total': total,
            'rate': ((present + late) / total * 100) if total > 0 else 0
        }
    
    @staticmethod
    def get_active_announcements(request) -> List:
        """Get active announcements."""
        from apps.communication.models import Announcement
        
        today = date.today()
        announcements = Announcement.objects.filter(
            is_active=True
        ).filter(
            Q(start_date__isnull=True) | Q(start_date__lte=today)
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today)
        ).order_by('-is_pinned', '-created_at')[:4]
        
        return list(announcements)
    
    @staticmethod
    def get_events_count(days: int = 30) -> int:
        """Get count of upcoming events."""
        from apps.events.models import Event
        
        today = date.today()
        return Event.objects.filter(
            start_date__gte=today,
            start_date__lte=today + timedelta(days=days),
            is_cancelled=False
        ).count()
    
    @staticmethod
    def get_groups_count() -> int:
        """Get count of active groups."""
        from apps.groups.models import Group
        
        return Group.objects.filter(is_active=True).count()
