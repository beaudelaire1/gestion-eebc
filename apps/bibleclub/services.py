"""
Service Layer pour le module Bible Club.

Ce module centralise la logique métier pour:
- La gestion des présences (AttendanceService)
- La gestion des sessions (SessionService)
- La gestion des enfants (ChildService)

Requirements: 7.5
"""

from datetime import date, timedelta
from typing import Optional, Dict, Any, List
from django.db.models import Count, Q, Avg
from django.utils import timezone

from .models import (
    AgeGroup, BibleClass, Child, Session, Attendance, Monitor, DriverCheckIn
)


class ServiceResult:
    """Résultat d'une opération de service."""
    
    def __init__(self, success: bool, data=None, error: str = None):
        self.success = success
        self.data = data
        self.error = error
    
    @classmethod
    def ok(cls, data=None):
        return cls(success=True, data=data)
    
    @classmethod
    def fail(cls, error: str):
        return cls(success=False, error=error)


class AttendanceService:
    """
    Service de gestion des présences au club biblique.
    
    Centralise la logique métier pour les opérations sur les présences,
    les statistiques et les rapports.
    """
    
    @classmethod
    def record_attendance(
        cls,
        session: Session,
        child: Child,
        status: str,
        recorded_by,
        check_in_time=None,
        notes: str = ''
    ) -> ServiceResult:
        """
        Enregistre ou met à jour la présence d'un enfant à une session.
        
        Args:
            session: La session concernée
            child: L'enfant concerné
            status: Le statut de présence (present, absent, late, excused, absent_notified)
            recorded_by: L'utilisateur qui enregistre
            check_in_time: Heure d'arrivée (optionnel)
            notes: Notes (optionnel)
        
        Returns:
            ServiceResult avec data={'attendance': attendance} si succès
        """
        try:
            # Valider le statut
            valid_statuses = [choice[0] for choice in Attendance.Status.choices]
            if status not in valid_statuses:
                return ServiceResult.fail(f"Statut invalide: {status}")
            
            # Vérifier que la session n'est pas annulée
            if session.is_cancelled:
                return ServiceResult.fail("Impossible d'enregistrer une présence pour une session annulée.")
            
            # Créer ou mettre à jour la présence
            attendance, created = Attendance.objects.get_or_create(
                session=session,
                child=child,
                defaults={
                    'bible_class': child.bible_class,
                    'status': status,
                    'recorded_by': recorded_by,
                    'notes': notes
                }
            )
            
            if not created:
                attendance.status = status
                attendance.recorded_by = recorded_by
                if notes:
                    attendance.notes = notes
            
            # Gérer l'heure d'arrivée
            if check_in_time:
                attendance.check_in_time = check_in_time
            elif status in ['present', 'late'] and not attendance.check_in_time:
                attendance.check_in_time = timezone.now().time()
            
            attendance.save()
            
            return ServiceResult.ok({'attendance': attendance, 'created': created})
            
        except Exception as e:
            return ServiceResult.fail(f"Erreur lors de l'enregistrement de la présence: {str(e)}")
    
    @classmethod
    def bulk_record_attendance(
        cls,
        session: Session,
        attendance_data: List[Dict[str, Any]],
        recorded_by
    ) -> ServiceResult:
        """
        Enregistre les présences pour plusieurs enfants en une fois.
        
        Args:
            session: La session concernée
            attendance_data: Liste de dictionnaires avec child_id, status, notes (optionnel)
            recorded_by: L'utilisateur qui enregistre
        
        Returns:
            ServiceResult avec data={'updated': count, 'errors': list} si succès
        """
        try:
            if session.is_cancelled:
                return ServiceResult.fail("Impossible d'enregistrer des présences pour une session annulée.")
            
            updated_count = 0
            errors = []
            
            for data in attendance_data:
                child_id = data.get('child_id')
                status = data.get('status')
                notes = data.get('notes', '')
                check_in_time = data.get('check_in_time')
                
                try:
                    child = Child.objects.get(pk=child_id)
                    result = cls.record_attendance(
                        session=session,
                        child=child,
                        status=status,
                        recorded_by=recorded_by,
                        check_in_time=check_in_time,
                        notes=notes
                    )
                    if result.success:
                        updated_count += 1
                    else:
                        errors.append({'child_id': child_id, 'error': result.error})
                except Child.DoesNotExist:
                    errors.append({'child_id': child_id, 'error': 'Enfant non trouvé'})
            
            return ServiceResult.ok({'updated': updated_count, 'errors': errors})
            
        except Exception as e:
            return ServiceResult.fail(f"Erreur lors de l'enregistrement des présences: {str(e)}")
    
    @classmethod
    def record_checkout(
        cls,
        attendance: Attendance,
        check_out_time,
        picked_up_by: str = ''
    ) -> ServiceResult:
        """
        Enregistre le départ d'un enfant.
        
        Args:
            attendance: L'enregistrement de présence
            check_out_time: Heure de départ
            picked_up_by: Personne qui récupère l'enfant (optionnel)
        
        Returns:
            ServiceResult avec data={'attendance': attendance} si succès
        """
        try:
            attendance.check_out_time = check_out_time
            if picked_up_by:
                attendance.picked_up_by = picked_up_by
            attendance.save()
            
            return ServiceResult.ok({'attendance': attendance})
            
        except Exception as e:
            return ServiceResult.fail(f"Erreur lors de l'enregistrement du départ: {str(e)}")
    
    @classmethod
    def initialize_session_attendance(
        cls,
        session: Session,
        bible_class: BibleClass = None
    ) -> ServiceResult:
        """
        Initialise les présences pour tous les enfants actifs d'une session.
        
        Args:
            session: La session concernée
            bible_class: Classe spécifique (optionnel, sinon toutes les classes)
        
        Returns:
            ServiceResult avec data={'created': count} si succès
        """
        try:
            if session.is_cancelled:
                return ServiceResult.fail("Impossible d'initialiser les présences pour une session annulée.")
            
            # Récupérer les enfants actifs
            children_qs = Child.objects.filter(is_active=True)
            if bible_class:
                children_qs = children_qs.filter(bible_class=bible_class)
            
            created_count = 0
            for child in children_qs:
                _, created = Attendance.objects.get_or_create(
                    session=session,
                    child=child,
                    defaults={
                        'bible_class': child.bible_class,
                        'status': Attendance.Status.ABSENT
                    }
                )
                if created:
                    created_count += 1
            
            return ServiceResult.ok({'created': created_count})
            
        except Exception as e:
            return ServiceResult.fail(f"Erreur lors de l'initialisation des présences: {str(e)}")
    
    @classmethod
    def get_session_stats(cls, session: Session, bible_class: BibleClass = None) -> Dict[str, Any]:
        """
        Retourne les statistiques de présence pour une session.
        
        Args:
            session: La session concernée
            bible_class: Classe spécifique (optionnel)
        
        Returns:
            Dictionnaire contenant les statistiques
        """
        attendances = session.attendances.all()
        if bible_class:
            attendances = attendances.filter(bible_class=bible_class)
        
        total = attendances.count()
        present = attendances.filter(status__in=['present', 'late']).count()
        absent = attendances.filter(status='absent').count()
        absent_notified = attendances.filter(status='absent_notified').count()
        excused = attendances.filter(status='excused').count()
        late = attendances.filter(status='late').count()
        
        attendance_rate = (present / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'present': present,
            'absent': absent,
            'absent_notified': absent_notified,
            'excused': excused,
            'late': late,
            'attendance_rate': round(attendance_rate, 1),
        }
    
    @classmethod
    def get_child_attendance_stats(
        cls,
        child: Child,
        start_date: date = None,
        end_date: date = None
    ) -> Dict[str, Any]:
        """
        Retourne les statistiques de présence pour un enfant.
        
        Args:
            child: L'enfant concerné
            start_date: Date de début (optionnel)
            end_date: Date de fin (optionnel)
        
        Returns:
            Dictionnaire contenant les statistiques
        """
        attendances = child.attendances.select_related('session')
        
        if start_date:
            attendances = attendances.filter(session__date__gte=start_date)
        if end_date:
            attendances = attendances.filter(session__date__lte=end_date)
        
        total = attendances.count()
        present = attendances.filter(status__in=['present', 'late']).count()
        absent = attendances.filter(status='absent').count()
        excused = attendances.filter(status='excused').count()
        late = attendances.filter(status='late').count()
        
        attendance_rate = (present / total * 100) if total > 0 else 0
        
        # Dernières présences
        recent_attendances = attendances.order_by('-session__date')[:10]
        
        return {
            'total_sessions': total,
            'present_count': present,
            'absent_count': absent,
            'excused_count': excused,
            'late_count': late,
            'attendance_rate': round(attendance_rate, 1),
            'recent_attendances': list(recent_attendances),
        }
    
    @classmethod
    def get_class_attendance_stats(
        cls,
        bible_class: BibleClass,
        start_date: date = None,
        end_date: date = None
    ) -> Dict[str, Any]:
        """
        Retourne les statistiques de présence pour une classe.
        
        Args:
            bible_class: La classe concernée
            start_date: Date de début (optionnel)
            end_date: Date de fin (optionnel)
        
        Returns:
            Dictionnaire contenant les statistiques
        """
        attendances = Attendance.objects.filter(bible_class=bible_class)
        
        if start_date:
            attendances = attendances.filter(session__date__gte=start_date)
        if end_date:
            attendances = attendances.filter(session__date__lte=end_date)
        
        total = attendances.count()
        present = attendances.filter(status__in=['present', 'late']).count()
        
        attendance_rate = (present / total * 100) if total > 0 else 0
        
        # Nombre d'enfants actifs dans la classe
        active_children = bible_class.children.filter(is_active=True).count()
        
        # Sessions avec cette classe
        sessions_count = attendances.values('session').distinct().count()
        
        return {
            'total_attendances': total,
            'present_count': present,
            'attendance_rate': round(attendance_rate, 1),
            'active_children': active_children,
            'sessions_count': sessions_count,
        }
    
    @classmethod
    def get_attendance_report(
        cls,
        start_date: date,
        end_date: date,
        bible_class: BibleClass = None
    ) -> Dict[str, Any]:
        """
        Génère un rapport de présence pour une période.
        
        Args:
            start_date: Date de début
            end_date: Date de fin
            bible_class: Classe spécifique (optionnel)
        
        Returns:
            Dictionnaire contenant le rapport
        """
        sessions = Session.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            is_cancelled=False
        ).order_by('date')
        
        report_data = []
        total_present = 0
        total_absent = 0
        total_children = 0
        
        for session in sessions:
            stats = cls.get_session_stats(session, bible_class)
            report_data.append({
                'session': session,
                'stats': stats
            })
            total_present += stats['present']
            total_absent += stats['absent'] + stats['absent_notified']
            total_children += stats['total']
        
        overall_rate = (total_present / total_children * 100) if total_children > 0 else 0
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'sessions': report_data,
            'total_sessions': sessions.count(),
            'total_present': total_present,
            'total_absent': total_absent,
            'overall_attendance_rate': round(overall_rate, 1),
        }
    
    @classmethod
    def get_attendance_chart_data(cls, months: int = 12) -> Dict[str, Any]:
        """
        Retourne les données de présence pour les graphiques.
        
        Args:
            months: Nombre de mois à analyser (défaut: 12)
        
        Returns:
            Dictionnaire avec labels (mois) et data (taux de présence)
        """
        from datetime import datetime
        from django.db.models import Count, Case, When, IntegerField
        from django.db.models.functions import TruncMonth
        
        # Calculer la date de début
        today = date.today()
        start_date = today.replace(day=1)
        for _ in range(months - 1):
            if start_date.month == 1:
                start_date = start_date.replace(year=start_date.year - 1, month=12)
            else:
                start_date = start_date.replace(month=start_date.month - 1)
        
        # Récupérer les sessions non annulées dans la période
        sessions = Session.objects.filter(
            date__gte=start_date,
            is_cancelled=False
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total_attendances=Count('attendances'),
            present_count=Count(
                Case(
                    When(attendances__status__in=['present', 'late'], then=1),
                    output_field=IntegerField()
                )
            )
        ).order_by('month')
        
        # Créer les labels et données pour tous les mois (même ceux sans données)
        labels = []
        data = []
        current_date = start_date
        
        # Convertir les résultats en dictionnaire pour un accès rapide
        monthly_stats = {}
        for item in sessions:
            month_key = item['month'].date().replace(day=1)
            total = item['total_attendances']
            present = item['present_count']
            rate = (present / total * 100) if total > 0 else 0
            monthly_stats[month_key] = round(rate, 1)
        
        for _ in range(months):
            # Format du label (ex: "Jan 2024")
            labels.append(current_date.strftime('%b %Y'))
            
            # Taux de présence pour ce mois (0 si pas de données)
            month_key = current_date
            data.append(monthly_stats.get(month_key, 0))
            
            # Passer au mois suivant
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        # Calculer les statistiques globales
        total_rate = sum(data) / len([x for x in data if x > 0]) if any(data) else 0
        
        return {
            'labels': labels,
            'data': data,
            'average_rate': round(total_rate, 1),
            'best_month': max(data) if data else 0,
            'worst_month': min([x for x in data if x > 0]) if any(data) else 0
        }



class SessionService:
    """
    Service de gestion des sessions du club biblique.
    
    Centralise la logique métier pour les opérations sur les sessions.
    """
    
    @classmethod
    def create_session(
        cls,
        session_date: date,
        theme: str = '',
        notes: str = '',
        auto_create_attendance: bool = True
    ) -> ServiceResult:
        """
        Crée une nouvelle session.
        
        Args:
            session_date: Date de la session
            theme: Thème de la session (optionnel)
            notes: Notes (optionnel)
            auto_create_attendance: Créer automatiquement les présences (défaut: True)
        
        Returns:
            ServiceResult avec data={'session': session, 'created': bool} si succès
        """
        try:
            session, created = Session.objects.get_or_create(
                date=session_date,
                defaults={'theme': theme, 'notes': notes}
            )
            
            if not created:
                return ServiceResult.ok({
                    'session': session,
                    'created': False,
                    'message': f"Une session existe déjà pour le {session_date}"
                })
            
            # Créer automatiquement les présences pour tous les enfants actifs
            if auto_create_attendance:
                result = AttendanceService.initialize_session_attendance(session)
                attendance_count = result.data.get('created', 0) if result.success else 0
            else:
                attendance_count = 0
            
            return ServiceResult.ok({
                'session': session,
                'created': True,
                'attendance_created': attendance_count
            })
            
        except Exception as e:
            return ServiceResult.fail(f"Erreur lors de la création de la session: {str(e)}")
    
    @classmethod
    def cancel_session(cls, session: Session, reason: str = '') -> ServiceResult:
        """
        Annule une session.
        
        Args:
            session: La session à annuler
            reason: Raison de l'annulation (optionnel)
        
        Returns:
            ServiceResult avec data={'session': session} si succès
        """
        try:
            if session.is_cancelled:
                return ServiceResult.fail("Cette session est déjà annulée.")
            
            session.is_cancelled = True
            if reason:
                session.notes = f"{session.notes}\n[Annulée]: {reason}".strip()
            session.save()
            
            return ServiceResult.ok({'session': session})
            
        except Exception as e:
            return ServiceResult.fail(f"Erreur lors de l'annulation de la session: {str(e)}")
    
    @classmethod
    def get_upcoming_sessions(cls, limit: int = 5) -> List[Session]:
        """
        Retourne les prochaines sessions.
        
        Args:
            limit: Nombre maximum de sessions à retourner
        
        Returns:
            Liste des sessions
        """
        today = date.today()
        return Session.objects.filter(
            date__gte=today,
            is_cancelled=False
        ).order_by('date')[:limit]
    
    @classmethod
    def get_recent_sessions(cls, limit: int = 5) -> List[Session]:
        """
        Retourne les sessions récentes.
        
        Args:
            limit: Nombre maximum de sessions à retourner
        
        Returns:
            Liste des sessions
        """
        return Session.objects.filter(
            is_cancelled=False
        ).order_by('-date')[:limit]
    
    @classmethod
    def get_next_sunday(cls) -> date:
        """
        Retourne la date du prochain dimanche.
        
        Returns:
            Date du prochain dimanche
        """
        today = date.today()
        days_until_sunday = (6 - today.weekday()) % 7
        if days_until_sunday == 0 and today.weekday() != 6:
            days_until_sunday = 7
        return today + timedelta(days=days_until_sunday)
    
    @classmethod
    def get_or_create_today_session(cls) -> ServiceResult:
        """
        Récupère ou crée la session du jour (si c'est dimanche).
        
        Returns:
            ServiceResult avec data={'session': session} si succès
        """
        today = date.today()
        if today.weekday() != 6:  # Pas dimanche
            return ServiceResult.fail("Aujourd'hui n'est pas un dimanche.")
        
        return cls.create_session(today)


class ChildService:
    """
    Service de gestion des enfants du club biblique.
    
    Centralise la logique métier pour les opérations sur les enfants.
    """
    
    @classmethod
    def get_children_by_class(
        cls,
        bible_class: BibleClass,
        active_only: bool = True
    ) -> List[Child]:
        """
        Retourne les enfants d'une classe.
        
        Args:
            bible_class: La classe concernée
            active_only: Seulement les enfants actifs (défaut: True)
        
        Returns:
            Liste des enfants
        """
        children = Child.objects.filter(bible_class=bible_class)
        if active_only:
            children = children.filter(is_active=True)
        return children.order_by('last_name', 'first_name')
    
    @classmethod
    def get_children_needing_transport(cls, active_only: bool = True) -> List[Child]:
        """
        Retourne les enfants ayant besoin de transport.
        
        Args:
            active_only: Seulement les enfants actifs (défaut: True)
        
        Returns:
            Liste des enfants
        """
        children = Child.objects.filter(needs_transport=True)
        if active_only:
            children = children.filter(is_active=True)
        return children.select_related('bible_class', 'assigned_driver')
    
    @classmethod
    def assign_to_class(cls, child: Child, bible_class: BibleClass) -> ServiceResult:
        """
        Assigne un enfant à une classe.
        
        Args:
            child: L'enfant à assigner
            bible_class: La classe cible
        
        Returns:
            ServiceResult avec data={'child': child} si succès
        """
        try:
            # Vérifier la capacité de la classe
            current_count = bible_class.children.filter(is_active=True).count()
            if current_count >= bible_class.max_capacity:
                return ServiceResult.fail(
                    f"La classe {bible_class} a atteint sa capacité maximale ({bible_class.max_capacity})."
                )
            
            # Vérifier l'âge de l'enfant
            age_group = bible_class.age_group
            if child.age < age_group.min_age or child.age > age_group.max_age:
                return ServiceResult.fail(
                    f"L'âge de l'enfant ({child.age} ans) ne correspond pas à la tranche d'âge "
                    f"de la classe ({age_group.min_age}-{age_group.max_age} ans)."
                )
            
            child.bible_class = bible_class
            child.save(update_fields=['bible_class'])
            
            return ServiceResult.ok({'child': child})
            
        except Exception as e:
            return ServiceResult.fail(f"Erreur lors de l'assignation à la classe: {str(e)}")
    
    @classmethod
    def get_dashboard_stats(cls, user=None) -> Dict[str, Any]:
        """
        Retourne les statistiques pour le dashboard du club biblique.
        
        Args:
            user: Utilisateur pour filtrer selon les permissions (optionnel)
        
        Returns:
            Dictionnaire contenant les statistiques
        """
        from .permissions import get_user_classes, is_club_admin
        
        # Déterminer les classes accessibles
        if user and not is_club_admin(user):
            user_classes = get_user_classes(user)
            children_filter = Q(bible_class__in=user_classes)
        else:
            children_filter = Q()
            user_classes = BibleClass.objects.filter(is_active=True)
        
        # Statistiques des enfants
        children_qs = Child.objects.filter(is_active=True)
        if children_filter:
            children_qs = children_qs.filter(children_filter)
        
        total_children = children_qs.count()
        boys_count = children_qs.filter(gender='M').count()
        girls_count = children_qs.filter(gender='F').count()
        transport_count = children_qs.filter(needs_transport=True).count()
        
        # Statistiques des classes
        total_classes = user_classes.count() if hasattr(user_classes, 'count') else user_classes.count()
        total_monitors = Monitor.objects.filter(is_active=True).count()
        
        # Prochaine session
        next_sunday = SessionService.get_next_sunday()
        
        return {
            'total_children': total_children,
            'boys_count': boys_count,
            'girls_count': girls_count,
            'transport_count': transport_count,
            'total_classes': total_classes,
            'total_monitors': total_monitors,
            'next_sunday': next_sunday,
        }
