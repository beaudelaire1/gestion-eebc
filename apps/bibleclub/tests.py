from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from datetime import date, timedelta

from .models import AgeGroup, BibleClass, Child, Session, Attendance, Monitor
from .permissions import (
    get_monitor_for_user, get_user_classes, can_access_class,
    can_access_child, is_club_staff, is_club_admin
)

User = get_user_model()


class AgeGroupTests(TestCase):
    """Tests pour le modele AgeGroup."""
    
    def test_create_age_group(self):
        """Test creation d'une tranche d'age."""
        ag = AgeGroup.objects.create(
            name='Petits',
            min_age=3,
            max_age=5
        )
        self.assertEqual(str(ag), 'Petits (3-5 ans)')
    
    def test_age_group_validation(self):
        """Test validation min_age < max_age."""
        from django.core.exceptions import ValidationError
        ag = AgeGroup(name='Invalid', min_age=10, max_age=5)
        with self.assertRaises(ValidationError):
            ag.clean()


class BibleClassTests(TestCase):
    """Tests pour le modele BibleClass."""
    
    def setUp(self):
        self.age_group = AgeGroup.objects.create(
            name='Moyens',
            min_age=6,
            max_age=8
        )
    
    def test_create_class(self):
        """Test creation d'une classe."""
        bc = BibleClass.objects.create(
            age_group=self.age_group,
            room='Salle 1'
        )
        self.assertIn('Moyens', str(bc))
        self.assertEqual(bc.children_count, 0)


class ChildTests(TestCase):
    """Tests pour le modele Child."""
    
    def setUp(self):
        self.age_group = AgeGroup.objects.create(
            name='Grands',
            min_age=9,
            max_age=12
        )
        self.bible_class = BibleClass.objects.create(
            age_group=self.age_group
        )
    
    def test_create_child(self):
        """Test creation d'un enfant."""
        # Utiliser une date fixe pour eviter les problemes d'anniversaire
        birth_date = date(2014, 1, 1)
        child = Child.objects.create(
            first_name='Lucas',
            last_name='Martin',
            date_of_birth=birth_date,
            gender='M',
            parent1_name='M. Martin',
            parent1_phone='0612345678',
            bible_class=self.bible_class
        )
        self.assertEqual(str(child), 'Lucas Martin')
        # L'age depend de la date actuelle, on verifie juste que c'est > 0
        self.assertGreater(child.age, 0)
    
    def test_child_class_count(self):
        """Test comptage enfants dans classe."""
        Child.objects.create(
            first_name='Emma',
            last_name='Bernard',
            date_of_birth=date.today() - timedelta(days=9*365),
            gender='F',
            parent1_name='Mme Bernard',
            parent1_phone='0698765432',
            bible_class=self.bible_class
        )
        self.assertEqual(self.bible_class.children_count, 1)


class SessionAttendanceTests(TestCase):
    """Tests pour le workflow de session et presence."""
    
    def setUp(self):
        self.age_group = AgeGroup.objects.create(
            name='Petits',
            min_age=3,
            max_age=5
        )
        self.bible_class = BibleClass.objects.create(
            age_group=self.age_group
        )
        self.child = Child.objects.create(
            first_name='Noah',
            last_name='Dubois',
            date_of_birth=date.today() - timedelta(days=4*365),
            gender='M',
            parent1_name='M. Dubois',
            parent1_phone='0611111111',
            bible_class=self.bible_class
        )
        self.session = Session.objects.create(
            date=date.today()
        )
    
    def test_create_attendance(self):
        """Test creation d'une presence."""
        attendance = Attendance.objects.create(
            session=self.session,
            child=self.child,
            bible_class=self.bible_class,
            status='present'
        )
        self.assertEqual(attendance.status, 'present')
    
    def test_attendance_status_change(self):
        """Test changement de statut de presence."""
        attendance = Attendance.objects.create(
            session=self.session,
            child=self.child,
            bible_class=self.bible_class,
            status='absent'
        )
        
        # Marquer present
        attendance.status = 'present'
        attendance.save()
        
        attendance.refresh_from_db()
        self.assertEqual(attendance.status, 'present')
    
    def test_unique_attendance(self):
        """Test unicite session/enfant."""
        Attendance.objects.create(
            session=self.session,
            child=self.child,
            bible_class=self.bible_class
        )
        
        # Tenter de creer un doublon doit echouer
        with self.assertRaises(Exception):
            Attendance.objects.create(
                session=self.session,
                child=self.child,
                bible_class=self.bible_class
            )


class MonitorTests(TestCase):
    """Tests pour le modele Monitor."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='moniteur_test',
            password='test123',
            first_name='Marie',
            last_name='Dupont',
            role='moniteur'
        )
        self.age_group = AgeGroup.objects.create(
            name='Moyens',
            min_age=6,
            max_age=8
        )
        self.bible_class = BibleClass.objects.create(
            age_group=self.age_group
        )
    
    def test_create_monitor(self):
        """Test creation d'un moniteur."""
        monitor = Monitor.objects.create(
            user=self.user,
            bible_class=self.bible_class,
            is_lead=True
        )
        self.assertEqual(str(monitor), 'Marie Dupont')
        self.assertTrue(monitor.is_lead)


class PermissionsTests(TestCase):
    """Tests pour le systeme de permissions du Club Biblique."""
    
    def setUp(self):
        # Creer les utilisateurs
        self.admin_user = User.objects.create_user(
            username='admin_club',
            password='test123',
            role='responsable_club'
        )
        self.moniteur_user = User.objects.create_user(
            username='moniteur1',
            password='test123',
            role='moniteur'
        )
        self.autre_moniteur = User.objects.create_user(
            username='moniteur2',
            password='test123',
            role='moniteur'
        )
        self.membre_user = User.objects.create_user(
            username='membre',
            password='test123',
            role='membre'
        )
        
        # Creer les classes
        self.age_group1 = AgeGroup.objects.create(name='Petits', min_age=3, max_age=5)
        self.age_group2 = AgeGroup.objects.create(name='Grands', min_age=9, max_age=12)
        
        self.classe1 = BibleClass.objects.create(age_group=self.age_group1, room='Salle 1')
        self.classe2 = BibleClass.objects.create(age_group=self.age_group2, room='Salle 2')
        
        # Assigner les moniteurs
        self.monitor1 = Monitor.objects.create(
            user=self.moniteur_user,
            bible_class=self.classe1,
            is_active=True
        )
        self.monitor2 = Monitor.objects.create(
            user=self.autre_moniteur,
            bible_class=self.classe2,
            is_active=True
        )
        
        # Creer des enfants
        self.enfant_classe1 = Child.objects.create(
            first_name='Lucas',
            last_name='Martin',
            date_of_birth=date.today() - timedelta(days=4*365),
            gender='M',
            parent1_name='M. Martin',
            parent1_phone='0612345678',
            bible_class=self.classe1
        )
        self.enfant_classe2 = Child.objects.create(
            first_name='Emma',
            last_name='Bernard',
            date_of_birth=date.today() - timedelta(days=10*365),
            gender='F',
            parent1_name='Mme Bernard',
            parent1_phone='0698765432',
            bible_class=self.classe2
        )
    
    def test_is_club_admin(self):
        """Test detection admin club."""
        self.assertTrue(is_club_admin(self.admin_user))
        self.assertFalse(is_club_admin(self.moniteur_user))
        self.assertFalse(is_club_admin(self.membre_user))
    
    def test_is_club_staff(self):
        """Test detection staff club."""
        self.assertTrue(is_club_staff(self.admin_user))
        self.assertTrue(is_club_staff(self.moniteur_user))
        self.assertFalse(is_club_staff(self.membre_user))
    
    def test_get_monitor_for_user(self):
        """Test recuperation profil moniteur."""
        monitor = get_monitor_for_user(self.moniteur_user)
        self.assertIsNotNone(monitor)
        self.assertEqual(monitor.bible_class, self.classe1)
        
        # Membre n'a pas de profil moniteur
        self.assertIsNone(get_monitor_for_user(self.membre_user))
    
    def test_get_user_classes_admin(self):
        """Test classes accessibles par admin."""
        classes = get_user_classes(self.admin_user)
        self.assertEqual(classes.count(), 2)
    
    def test_get_user_classes_moniteur(self):
        """Test classes accessibles par moniteur."""
        classes = get_user_classes(self.moniteur_user)
        self.assertEqual(classes.count(), 1)
        self.assertEqual(classes.first(), self.classe1)
    
    def test_can_access_class_admin(self):
        """Test acces classe par admin."""
        self.assertTrue(can_access_class(self.admin_user, self.classe1))
        self.assertTrue(can_access_class(self.admin_user, self.classe2))
    
    def test_can_access_class_moniteur(self):
        """Test acces classe par moniteur."""
        # Moniteur 1 peut acceder a sa classe
        self.assertTrue(can_access_class(self.moniteur_user, self.classe1))
        # Moniteur 1 ne peut pas acceder a l'autre classe
        self.assertFalse(can_access_class(self.moniteur_user, self.classe2))
    
    def test_can_access_child_admin(self):
        """Test acces enfant par admin."""
        self.assertTrue(can_access_child(self.admin_user, self.enfant_classe1))
        self.assertTrue(can_access_child(self.admin_user, self.enfant_classe2))
    
    def test_can_access_child_moniteur(self):
        """Test acces enfant par moniteur."""
        # Moniteur 1 peut acceder aux enfants de sa classe
        self.assertTrue(can_access_child(self.moniteur_user, self.enfant_classe1))
        # Moniteur 1 ne peut pas acceder aux enfants de l'autre classe
        self.assertFalse(can_access_child(self.moniteur_user, self.enfant_classe2))


class PermissionsViewsTests(TestCase):
    """Tests des vues avec permissions."""
    
    def setUp(self):
        self.client = Client()
        
        # Creer les utilisateurs
        self.admin_user = User.objects.create_user(
            username='admin_club',
            password='test123',
            role='responsable_club'
        )
        self.moniteur_user = User.objects.create_user(
            username='moniteur1',
            password='test123',
            role='moniteur'
        )
        self.membre_user = User.objects.create_user(
            username='membre',
            password='test123',
            role='membre'
        )
        
        # Creer les classes
        self.age_group = AgeGroup.objects.create(name='Petits', min_age=3, max_age=5)
        self.classe1 = BibleClass.objects.create(age_group=self.age_group, room='Salle 1')
        self.classe2 = BibleClass.objects.create(
            age_group=AgeGroup.objects.create(name='Grands', min_age=9, max_age=12),
            room='Salle 2'
        )
        
        # Assigner le moniteur
        self.monitor = Monitor.objects.create(
            user=self.moniteur_user,
            bible_class=self.classe1,
            is_active=True
        )
        
        # Creer un enfant
        self.enfant = Child.objects.create(
            first_name='Lucas',
            last_name='Martin',
            date_of_birth=date.today() - timedelta(days=4*365),
            gender='M',
            parent1_name='M. Martin',
            parent1_phone='0612345678',
            bible_class=self.classe1
        )
        
        # Creer une session
        self.session = Session.objects.create(date=date.today())
    
    def test_membre_cannot_access_bibleclub(self):
        """Test qu'un membre simple ne peut pas acceder au club biblique."""
        self.client.login(username='membre', password='test123')
        response = self.client.get(reverse('bibleclub:home'))
        # Devrait rediriger vers dashboard
        self.assertEqual(response.status_code, 302)
    
    def test_moniteur_can_access_bibleclub(self):
        """Test qu'un moniteur peut acceder au club biblique."""
        self.client.login(username='moniteur1', password='test123')
        response = self.client.get(reverse('bibleclub:home'))
        self.assertEqual(response.status_code, 200)
    
    def test_moniteur_can_access_own_class(self):
        """Test qu'un moniteur peut acceder a sa classe."""
        self.client.login(username='moniteur1', password='test123')
        response = self.client.get(reverse('bibleclub:class_detail', args=[self.classe1.pk]))
        self.assertEqual(response.status_code, 200)
    
    def test_moniteur_cannot_access_other_class(self):
        """Test qu'un moniteur ne peut pas acceder a une autre classe."""
        self.client.login(username='moniteur1', password='test123')
        response = self.client.get(reverse('bibleclub:class_detail', args=[self.classe2.pk]))
        # Devrait rediriger
        self.assertEqual(response.status_code, 302)
    
    def test_moniteur_cannot_create_session(self):
        """Test qu'un moniteur ne peut pas creer de session."""
        self.client.login(username='moniteur1', password='test123')
        response = self.client.get(reverse('bibleclub:create_session'))
        # Devrait rediriger
        self.assertEqual(response.status_code, 302)
    
    def test_admin_can_create_session(self):
        """Test qu'un admin peut creer une session."""
        self.client.login(username='admin_club', password='test123')
        response = self.client.get(reverse('bibleclub:create_session'))
        self.assertEqual(response.status_code, 200)

