from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta

from .models import AgeGroup, BibleClass, Child, Session, Attendance, Monitor

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

