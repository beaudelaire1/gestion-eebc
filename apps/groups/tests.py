from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.members.models import Member
from .models import Group, GroupMeeting
from .services import GroupService, GroupMeetingService
from datetime import date, time

User = get_user_model()


class GroupModelTest(TestCase):
    """Tests pour le modèle Group."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role='admin'
        )
        
    def test_group_creation(self):
        """Test de création d'un groupe."""
        group = Group.objects.create(
            name='Test Group',
            description='Test description',
            group_type='youth',
            leader=self.user,
            meeting_day='sunday',
            meeting_time=time(10, 0),
            meeting_location='Salle 1'
        )
        
        self.assertEqual(group.name, 'Test Group')
        self.assertEqual(group.leader, self.user)
        self.assertEqual(group.member_count, 0)
        
    def test_group_str_representation(self):
        """Test de la représentation string du groupe."""
        group = Group.objects.create(name='Test Group')
        self.assertEqual(str(group), 'Test Group')


class GroupMeetingModelTest(TestCase):
    """Tests pour le modèle GroupMeeting."""
    
    def setUp(self):
        self.group = Group.objects.create(
            name='Test Group',
            group_type='youth'
        )
        
    def test_meeting_creation(self):
        """Test de création d'une réunion."""
        meeting = GroupMeeting.objects.create(
            group=self.group,
            date=date.today(),
            time=time(10, 0),
            topic='Test Meeting',
            attendees_count=5
        )
        
        self.assertEqual(meeting.group, self.group)
        self.assertEqual(meeting.attendees_count, 5)
        self.assertFalse(meeting.is_cancelled)
        
    def test_meeting_str_representation(self):
        """Test de la représentation string de la réunion."""
        meeting = GroupMeeting.objects.create(
            group=self.group,
            date=date.today()
        )
        expected = f"{self.group.name} - {date.today()}"
        self.assertEqual(str(meeting), expected)


class GroupServiceTest(TestCase):
    """Tests pour GroupService."""
    
    def setUp(self):
        self.group = Group.objects.create(
            name='Test Group',
            group_type='youth'
        )
        
        # Créer quelques réunions de test
        GroupMeeting.objects.create(
            group=self.group,
            date=date.today(),
            attendees_count=10
        )
        GroupMeeting.objects.create(
            group=self.group,
            date=date.today(),
            attendees_count=8
        )
        
    def test_get_group_statistics(self):
        """Test des statistiques de groupe."""
        stats = GroupService.get_group_statistics(self.group)
        
        self.assertEqual(stats['total_meetings'], 2)
        self.assertEqual(stats['avg_attendance'], 9.0)
        self.assertEqual(stats['member_count'], 0)
        
    def test_get_attendance_chart_data(self):
        """Test des données pour le graphique."""
        chart_data = GroupService.get_attendance_chart_data(self.group)
        
        self.assertEqual(len(chart_data), 2)
        self.assertIn('date', chart_data[0])
        self.assertIn('attendees', chart_data[0])


class GroupMeetingServiceTest(TestCase):
    """Tests pour GroupMeetingService."""
    
    def setUp(self):
        self.group = Group.objects.create(
            name='Test Group',
            group_type='youth',
            meeting_time=time(10, 0),
            meeting_location='Salle 1'
        )
        
    def test_create_meeting(self):
        """Test de création de réunion via le service."""
        meeting = GroupMeetingService.create_meeting(
            group=self.group,
            date=date.today(),
            topic='Test Meeting'
        )
        
        self.assertEqual(meeting.group, self.group)
        self.assertEqual(meeting.time, time(10, 0))
        self.assertEqual(meeting.location, 'Salle 1')
        self.assertEqual(meeting.topic, 'Test Meeting')
        
    def test_update_attendance(self):
        """Test de mise à jour de la présence."""
        meeting = GroupMeeting.objects.create(
            group=self.group,
            date=date.today()
        )
        
        updated_meeting = GroupMeetingService.update_attendance(
            meeting, 15, "Bonne participation"
        )
        
        self.assertEqual(updated_meeting.attendees_count, 15)
        self.assertEqual(updated_meeting.notes, "Bonne participation")
        
    def test_cancel_meeting(self):
        """Test d'annulation de réunion."""
        meeting = GroupMeeting.objects.create(
            group=self.group,
            date=date.today()
        )
        
        cancelled_meeting = GroupMeetingService.cancel_meeting(
            meeting, "Raison d'annulation"
        )
        
        self.assertTrue(cancelled_meeting.is_cancelled)
        self.assertIn("Annulé: Raison d'annulation", cancelled_meeting.notes)


class GroupViewsTest(TestCase):
    """Tests pour les vues Groups."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role='admin'
        )
        self.client.login(username='testuser', password='testpass123')
        
        self.group = Group.objects.create(
            name='Test Group',
            group_type='youth',
            leader=self.user
        )
        
    def test_group_list_view(self):
        """Test de la vue liste des groupes."""
        response = self.client.get(reverse('groups:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Group')
        
    def test_group_detail_view(self):
        """Test de la vue détail du groupe."""
        response = self.client.get(reverse('groups:detail', kwargs={'pk': self.group.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Group')
        
    def test_group_create_view_get(self):
        """Test de la vue création de groupe (GET)."""
        response = self.client.get(reverse('groups:create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Créer un groupe')
        
    def test_group_create_view_post(self):
        """Test de la vue création de groupe (POST)."""
        data = {
            'name': 'New Group',
            'description': 'New description',
            'group_type': 'choir',
            'leader': self.user.pk,
            'color': '#ff0000'
        }
        response = self.client.post(reverse('groups:create'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after creation
        
        # Vérifier que le groupe a été créé
        new_group = Group.objects.get(name='New Group')
        self.assertEqual(new_group.group_type, 'choir')
        self.assertEqual(new_group.leader, self.user)
        
    def test_group_statistics_view(self):
        """Test de la vue statistiques."""
        response = self.client.get(reverse('groups:statistics', kwargs={'pk': self.group.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Statistiques de présence')
        
    def test_groups_dashboard_view(self):
        """Test de la vue dashboard."""
        response = self.client.get(reverse('groups:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard des Groupes')


class GroupPermissionsTest(TestCase):
    """Tests des permissions pour les groupes."""
    
    def setUp(self):
        self.client = Client()
        
        # Utilisateur admin
        self.admin_user = User.objects.create_user(
            username='admin',
            password='testpass123',
            role='admin'
        )
        
        # Utilisateur responsable de groupe
        self.leader_user = User.objects.create_user(
            username='leader',
            password='testpass123',
            role='responsable_groupe'
        )
        
        # Utilisateur membre simple
        self.member_user = User.objects.create_user(
            username='member',
            password='testpass123',
            role='membre'
        )
        
        self.group = Group.objects.create(
            name='Test Group',
            group_type='youth',
            leader=self.leader_user
        )
        
    def test_admin_can_create_group(self):
        """Test qu'un admin peut créer un groupe."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('groups:create'))
        self.assertEqual(response.status_code, 200)
        
    def test_leader_can_edit_own_group(self):
        """Test qu'un responsable peut modifier son propre groupe."""
        self.client.login(username='leader', password='testpass123')
        response = self.client.get(reverse('groups:update', kwargs={'pk': self.group.pk}))
        self.assertEqual(response.status_code, 200)
        
    def test_member_cannot_create_group(self):
        """Test qu'un membre simple ne peut pas créer de groupe."""
        self.client.login(username='member', password='testpass123')
        response = self.client.get(reverse('groups:create'))
        self.assertEqual(response.status_code, 302)  # Redirect due to permission denied