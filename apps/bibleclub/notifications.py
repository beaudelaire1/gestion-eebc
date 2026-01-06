"""
Service de notifications pour le Club Biblique.
Couche métier - logique spécifique au domaine.
"""
from apps.core.infrastructure.email_backend import EmailBackend


class BibleClubNotificationService:
    """
    Service de notifications spécifique au Club Biblique.
    Contient la logique métier des notifications.
    """
    
    @staticmethod
    def notify_parents_of_absence(child, session):
        """
        Notifie tous les parents d'un enfant de son absence.
        
        Args:
            child: Instance de Child
            session: Instance de Session
            
        Returns:
            list[EmailLog]: Liste des logs d'emails envoyés
        """
        logs = []
        
        context = {
            'child': child,
            'session': session,
            'bible_class': child.bible_class,
        }
        
        # Notifier le père
        if child.father_email:
            log = EmailBackend.send_email(
                recipient_email=child.father_email,
                recipient_name=child.father_name,
                subject=f"Absence de {child.first_name} - Club Biblique EEBC",
                template_name='bibleclub/emails/absence_notification.html',
                context={**context, 'parent_name': child.father_name}
            )
            logs.append(log)
        
        # Notifier la mère
        if child.mother_email:
            log = EmailBackend.send_email(
                recipient_email=child.mother_email,
                recipient_name=child.mother_name,
                subject=f"Absence de {child.first_name} - Club Biblique EEBC",
                template_name='bibleclub/emails/absence_notification.html',
                context={**context, 'parent_name': child.mother_name}
            )
            logs.append(log)
        
        return logs
    
    @staticmethod
    def notify_recurring_absence(child, absences, threshold=3):
        """
        Notifie les parents d'absences récurrentes.
        
        Args:
            child: Instance de Child
            absences: QuerySet des absences récentes
            threshold: Seuil d'absences pour déclencher la notification
            
        Returns:
            list[EmailLog]: Liste des logs d'emails envoyés
        """
        logs = []
        
        context = {
            'child': child,
            'absences': absences,
            'absence_count': absences.count(),
            'threshold': threshold,
            'bible_class': child.bible_class,
        }
        
        subject = f"⚠️ Absences récurrentes de {child.first_name} - Club Biblique"
        
        # Notifier le père
        if child.father_email:
            log = EmailBackend.send_email(
                recipient_email=child.father_email,
                recipient_name=child.father_name,
                subject=subject,
                template_name='bibleclub/emails/recurring_absence.html',
                context={**context, 'parent_name': child.father_name}
            )
            logs.append(log)
        
        # Notifier la mère
        if child.mother_email:
            log = EmailBackend.send_email(
                recipient_email=child.mother_email,
                recipient_name=child.mother_name,
                subject=subject,
                template_name='bibleclub/emails/recurring_absence.html',
                context={**context, 'parent_name': child.mother_name}
            )
            logs.append(log)
        
        return logs
    
    @staticmethod
    def notify_session_completed(session, recipients, stats=None):
        """
        Notifie la fin d'une session avec les statistiques.
        
        Args:
            session: Instance de Session
            recipients: Liste de tuples (email, name)
            stats: Dictionnaire des statistiques (optionnel)
            
        Returns:
            list[EmailLog]: Liste des logs d'emails envoyés
        """
        if stats is None:
            # Calculer les stats si non fournies
            from apps.bibleclub.models import Attendance
            attendances = Attendance.objects.filter(session=session)
            present = attendances.filter(status='present').count()
            absent = attendances.exclude(status='present').count()
            total = present + absent
            stats = {
                'present': present,
                'absent': absent,
                'total': total,
                'attendance_rate': round((present / total * 100) if total > 0 else 0),
            }
        
        context = {
            'session': session,
            'stats': stats,
        }
        
        logs = []
        for email, name in recipients:
            log = EmailBackend.send_email(
                recipient_email=email,
                recipient_name=name,
                subject=f"✅ Session terminée - {session.date}",
                template_name='bibleclub/emails/session_completed.html',
                context={**context, 'recipient_name': name}
            )
            logs.append(log)
        
        return logs
    
    @staticmethod
    def check_and_notify_recurring_absences(child, threshold=3):
        """
        Vérifie et notifie les absences récurrentes d'un enfant.
        
        Args:
            child: Instance de Child
            threshold: Nombre d'absences consécutives pour déclencher la notification
            
        Returns:
            list[EmailLog] ou liste vide si pas de notification envoyée
        """
        from apps.bibleclub.models import Attendance
        
        # Récupérer les dernières présences
        recent_attendances = Attendance.objects.filter(
            child=child
        ).order_by('-session__date')[:threshold]
        
        # Vérifier si toutes sont des absences
        if recent_attendances.count() >= threshold:
            all_absent = all(
                att.status in ['absent', 'absent_notified'] 
                for att in recent_attendances
            )
            
            if all_absent:
                return BibleClubNotificationService.notify_recurring_absence(
                    child=child,
                    absences=recent_attendances,
                    threshold=threshold
                )
        
        return []