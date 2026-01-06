"""
Services optimisés pour le Club Biblique.
"""
from django.db.models import Count, Q, Prefetch
from django.core.cache import cache
from django.conf import settings
from apps.core.decorators import cache_result, handle_external_service_errors
from .models import Child, Session, Attendance, BibleClass, Monitor


class OptimizedBibleClubService:
    """
    Service optimisé pour les opérations du Club Biblique.
    Évite les requêtes N+1 et utilise le cache intelligemment.
    """
    
    @staticmethod
    @cache_result(timeout=300, key_prefix='bibleclub_stats')
    def get_dashboard_stats(user):
        """
        Récupère les statistiques du dashboard de manière optimisée.
        """
        from .permissions import is_club_admin, get_monitor_for_user
        
        if is_club_admin(user):
            # Stats globales pour les admins
            stats = {
                'total_children': Child.objects.filter(is_active=True).count(),
                'total_classes': BibleClass.objects.filter(is_active=True).count(),
                'total_monitors': Monitor.objects.filter(is_active=True).count(),
            }
        else:
            # Stats spécifiques au moniteur
            monitor = get_monitor_for_user(user)
            if monitor and monitor.bible_class:
                stats = {
                    'total_children': monitor.bible_class.children.filter(is_active=True).count(),
                    'total_classes': 1,
                    'total_monitors': monitor.bible_class.monitors.filter(is_active=True).count(),
                }
            else:
                stats = {
                    'total_children': 0,
                    'total_classes': 0,
                    'total_monitors': 0,
                }
        
        return stats
    
    @staticmethod
    def get_children_with_attendance_stats(bible_class=None):
        """
        Récupère les enfants avec leurs statistiques de présence.
        Évite les requêtes N+1.
        """
        queryset = Child.objects.select_related(
            'bible_class__age_group'
        ).prefetch_related(
            Prefetch(
                'attendances',
                queryset=Attendance.objects.select_related('session').order_by('-session__date')
            )
        )
        
        if bible_class:
            queryset = queryset.filter(bible_class=bible_class)
        
        # Annoter avec les statistiques
        queryset = queryset.annotate(
            total_sessions=Count('attendances'),
            present_count=Count('attendances', filter=Q(attendances__status='present')),
            absent_count=Count('attendances', filter=Q(attendances__status__in=['absent', 'absent_notified']))
        )
        
        return queryset.filter(is_active=True)
    
    @staticmethod
    def get_recent_sessions_with_stats(limit=5):
        """
        Récupère les sessions récentes avec leurs statistiques.
        """
        return Session.objects.select_related().prefetch_related(
            Prefetch(
                'attendances',
                queryset=Attendance.objects.select_related('child', 'bible_class')
            )
        ).annotate(
            total_children=Count('attendances'),
            present_count=Count('attendances', filter=Q(attendances__status='present')),
            absent_count=Count('attendances', filter=Q(attendances__status__in=['absent', 'absent_notified']))
        ).order_by('-date')[:limit]
    
    @staticmethod
    @cache_result(timeout=600, key_prefix='attendance_chart')
    def get_attendance_chart_data(months=12):
        """
        Génère les données pour le graphique de présences.
        Cache pendant 10 minutes.
        """
        from datetime import date, timedelta
        from django.db.models import Count
        
        end_date = date.today()
        start_date = end_date - timedelta(days=30 * months)
        
        # Récupérer les sessions avec leurs statistiques
        sessions = Session.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).annotate(
            present_count=Count('attendances', filter=Q(attendances__status='present')),
            total_count=Count('attendances')
        ).order_by('date')
        
        # Formater pour le graphique
        chart_data = {
            'labels': [],
            'datasets': [{
                'label': 'Présents',
                'data': [],
                'backgroundColor': 'rgba(10, 54, 255, 0.8)',
                'borderColor': 'rgba(10, 54, 255, 1)',
                'borderWidth': 2
            }, {
                'label': 'Total inscrits',
                'data': [],
                'backgroundColor': 'rgba(108, 117, 125, 0.3)',
                'borderColor': 'rgba(108, 117, 125, 1)',
                'borderWidth': 1
            }]
        }
        
        for session in sessions:
            chart_data['labels'].append(session.date.strftime('%d/%m'))
            chart_data['datasets'][0]['data'].append(session.present_count)
            chart_data['datasets'][1]['data'].append(session.total_count)
        
        return chart_data
    
    @staticmethod
    @handle_external_service_errors
    def process_attendance_batch(session, attendance_data):
        """
        Traite un lot de présences de manière optimisée.
        
        Args:
            session: Instance de Session
            attendance_data: Liste de dictionnaires {child_id, status, notes}
        """
        from apps.bibleclub.notifications import BibleClubNotificationService
        
        # Récupérer tous les enfants en une requête
        child_ids = [data['child_id'] for data in attendance_data]
        children = Child.objects.filter(id__in=child_ids).select_related('bible_class')
        children_dict = {child.id: child for child in children}
        
        # Créer/mettre à jour les présences en lot
        attendances_to_create = []
        attendances_to_update = []
        
        for data in attendance_data:
            child = children_dict.get(data['child_id'])
            if not child:
                continue
            
            attendance, created = Attendance.objects.get_or_create(
                session=session,
                child=child,
                defaults={
                    'bible_class': child.bible_class,
                    'status': data['status'],
                    'notes': data.get('notes', '')
                }
            )
            
            if not created and attendance.status != data['status']:
                attendance.status = data['status']
                attendance.notes = data.get('notes', '')
                attendances_to_update.append(attendance)
        
        # Mise à jour en lot
        if attendances_to_update:
            Attendance.objects.bulk_update(attendances_to_update, ['status', 'notes'])
        
        # Notifications d'absence (traitement asynchrone recommandé)
        absent_children = [
            children_dict[data['child_id']] 
            for data in attendance_data 
            if data['status'] in ['absent', 'absent_notified'] and data['child_id'] in children_dict
        ]
        
        for child in absent_children:
            # Vérifier les absences récurrentes
            BibleClubNotificationService.check_and_notify_recurring_absences(child)
        
        return {
            'success': True,
            'processed': len(attendance_data),
            'absent_notifications': len(absent_children)
        }
    
    @staticmethod
    def get_class_performance_report(bible_class, months=6):
        """
        Génère un rapport de performance pour une classe.
        """
        from datetime import date, timedelta
        
        end_date = date.today()
        start_date = end_date - timedelta(days=30 * months)
        
        # Sessions de la période
        sessions = Session.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).prefetch_related(
            Prefetch(
                'attendances',
                queryset=Attendance.objects.filter(bible_class=bible_class).select_related('child')
            )
        )
        
        # Statistiques par enfant
        children_stats = {}
        total_sessions = sessions.count()
        
        for session in sessions:
            for attendance in session.attendances.all():
                child_id = attendance.child.id
                if child_id not in children_stats:
                    children_stats[child_id] = {
                        'child': attendance.child,
                        'present': 0,
                        'absent': 0,
                        'late': 0,
                        'excused': 0
                    }
                
                if attendance.status == 'present':
                    children_stats[child_id]['present'] += 1
                elif attendance.status in ['absent', 'absent_notified']:
                    children_stats[child_id]['absent'] += 1
                elif attendance.status == 'late':
                    children_stats[child_id]['late'] += 1
                elif attendance.status == 'excused':
                    children_stats[child_id]['excused'] += 1
        
        # Calculer les taux de présence
        for stats in children_stats.values():
            total_child_sessions = sum([stats['present'], stats['absent'], stats['late'], stats['excused']])
            if total_child_sessions > 0:
                stats['attendance_rate'] = round((stats['present'] / total_child_sessions) * 100, 1)
            else:
                stats['attendance_rate'] = 0
        
        return {
            'bible_class': bible_class,
            'period': f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}",
            'total_sessions': total_sessions,
            'children_stats': list(children_stats.values()),
            'class_average': round(
                sum(stats['attendance_rate'] for stats in children_stats.values()) / len(children_stats)
                if children_stats else 0, 1
            )
        }