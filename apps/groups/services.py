from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import datetime, timedelta
from .models import Group, GroupMeeting


class GroupService:
    """Service pour la gestion des groupes."""
    
    @staticmethod
    def get_group_statistics(group, months=6):
        """Obtenir les statistiques d'un groupe."""
        start_date = timezone.now().date() - timedelta(days=months * 30)
        
        meetings = group.meetings.filter(
            is_cancelled=False,
            date__gte=start_date
        )
        
        stats = meetings.aggregate(
            total_meetings=Count('id'),
            avg_attendance=Avg('attendees_count'),
            max_attendance=Count('attendees_count')
        )
        
        # Calculer le taux de présence
        if group.member_count > 0 and stats['avg_attendance']:
            attendance_rate = (stats['avg_attendance'] / group.member_count) * 100
        else:
            attendance_rate = 0
        
        return {
            'total_meetings': stats['total_meetings'] or 0,
            'avg_attendance': stats['avg_attendance'] or 0,
            'max_attendance': stats['max_attendance'] or 0,
            'attendance_rate': attendance_rate,
            'member_count': group.member_count
        }
    
    @staticmethod
    def get_attendance_chart_data(group, months=6):
        """Obtenir les données pour le graphique de présence."""
        start_date = timezone.now().date() - timedelta(days=months * 30)
        
        meetings = group.meetings.filter(
            is_cancelled=False,
            date__gte=start_date
        ).order_by('date')
        
        chart_data = []
        for meeting in meetings:
            chart_data.append({
                'date': meeting.date.strftime('%Y-%m-%d'),
                'attendees': meeting.attendees_count,
                'topic': meeting.topic or 'Réunion',
                'location': meeting.location or group.meeting_location
            })
        
        return chart_data


class GroupMeetingService:
    """Service pour la gestion des réunions de groupe."""
    
    @staticmethod
    def create_meeting(group, date, time=None, location=None, topic=None, notes=None):
        """Créer une nouvelle réunion."""
        meeting = GroupMeeting.objects.create(
            group=group,
            date=date,
            time=time or group.meeting_time,
            location=location or group.meeting_location,
            topic=topic or '',
            notes=notes or ''
        )
        return meeting
    
    @staticmethod
    def update_attendance(meeting, attendees_count, notes=None):
        """Mettre à jour la présence d'une réunion."""
        meeting.attendees_count = attendees_count
        if notes is not None:
            meeting.notes = notes
        meeting.save()
        return meeting
    
    @staticmethod
    def cancel_meeting(meeting, reason=None):
        """Annuler une réunion."""
        meeting.is_cancelled = True
        if reason:
            if meeting.notes:
                meeting.notes += f"\n\nAnnulé: {reason}"
            else:
                meeting.notes = f"Annulé: {reason}"
        meeting.save()
        return meeting
    
    @staticmethod
    def get_upcoming_meetings(group, days=30):
        """Obtenir les prochaines réunions d'un groupe."""
        end_date = timezone.now().date() + timedelta(days=days)
        
        return group.meetings.filter(
            is_cancelled=False,
            date__gte=timezone.now().date(),
            date__lte=end_date
        ).order_by('date')
    
    @staticmethod
    def get_recent_meetings(group, count=5):
        """Obtenir les réunions récentes d'un groupe."""
        return group.meetings.filter(
            is_cancelled=False
        ).order_by('-date')[:count]
    
    @staticmethod
    def generate_recurring_meetings(group, start_date, end_date):
        """Générer des réunions récurrentes basées sur les paramètres du groupe."""
        if not group.meeting_day or not group.meeting_frequency:
            return []
        
        meetings = []
        current_date = start_date
        
        # Mapping des jours de la semaine
        weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        target_weekday = weekdays.get(group.meeting_day)
        if target_weekday is None:
            return []
        
        # Trouver le premier jour correspondant
        days_ahead = target_weekday - current_date.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        current_date += timedelta(days=days_ahead)
        
        # Déterminer l'intervalle selon la fréquence
        if group.meeting_frequency == 'weekly':
            interval = 7
        elif group.meeting_frequency == 'biweekly':
            interval = 14
        elif group.meeting_frequency == 'monthly':
            interval = 28  # Approximation pour mensuel
        else:
            interval = 7
        
        # Générer les réunions
        while current_date <= end_date:
            # Vérifier qu'il n'y a pas déjà une réunion ce jour-là
            existing = GroupMeeting.objects.filter(
                group=group,
                date=current_date
            ).exists()
            
            if not existing:
                meeting = GroupMeeting(
                    group=group,
                    date=current_date,
                    time=group.meeting_time,
                    location=group.meeting_location,
                    topic=f"Réunion {group.get_meeting_frequency_display().lower()}"
                )
                meetings.append(meeting)
            
            current_date += timedelta(days=interval)
        
        return meetings
    
    @staticmethod
    def bulk_create_meetings(meetings):
        """Créer plusieurs réunions en lot."""
        return GroupMeeting.objects.bulk_create(meetings)


class GroupMembershipService:
    """Service pour la gestion des membres de groupe."""
    
    @staticmethod
    def add_member(group, member):
        """Ajouter un membre à un groupe."""
        group.members.add(member)
        return True
    
    @staticmethod
    def remove_member(group, member):
        """Retirer un membre d'un groupe."""
        group.members.remove(member)
        return True
    
    @staticmethod
    def bulk_update_members(group, member_ids):
        """Mettre à jour les membres d'un groupe en lot."""
        group.members.set(member_ids)
        return group.members.count()
    
    @staticmethod
    def get_member_groups(member):
        """Obtenir tous les groupes d'un membre."""
        return member.groups.filter(is_active=True)
    
    @staticmethod
    def get_group_members_with_stats(group):
        """Obtenir les membres avec leurs statistiques de présence."""
        members = group.members.all()
        
        # Pour chaque membre, calculer ses statistiques
        # (Cette fonctionnalité pourrait être étendue avec un modèle de présence individuelle)
        
        return members