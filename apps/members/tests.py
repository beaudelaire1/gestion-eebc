from django.test import TestCase
from datetime import date, timedelta

from .models import Member


class MemberTests(TestCase):
    """Tests pour le modele Member."""
    
    def test_create_member(self):
        """Test creation d'un membre."""
        member = Member.objects.create(
            first_name='Jacques',
            last_name='Laurent',
            email='jacques@test.com',
            phone='0612345678',
            status='actif'
        )
        self.assertEqual(str(member), 'Jacques Laurent')
        self.assertEqual(member.full_name, 'Jacques Laurent')
    
    def test_member_age(self):
        """Test calcul de l'age."""
        # Utiliser une date fixe
        birth_date = date(1994, 1, 1)
        member = Member.objects.create(
            first_name='Sophie',
            last_name='Bernard',
            date_of_birth=birth_date
        )
        # Verifier que l'age est calcule et positif
        self.assertIsNotNone(member.age)
        self.assertGreater(member.age, 25)
    
    def test_member_status(self):
        """Test statuts du membre."""
        member = Member.objects.create(
            first_name='Test',
            last_name='Member',
            status='visiteur'
        )
        self.assertEqual(member.status, 'visiteur')
        self.assertEqual(member.get_status_display(), 'Visiteur')

