"""
Factories pour générer les données de test avec factory_boy.
"""

import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
import random

from apps.core.models import Site
from apps.members.models import Member
from apps.events.models import Event, EventCategory
from apps.finance.models import FinancialTransaction, FinanceCategory
from apps.accounts.models import User as CustomUser

User = get_user_model()


class SiteFactory(DjangoModelFactory):
    """Factory pour créer des sites de test."""
    
    class Meta:
        model = Site
    
    code = factory.Sequence(lambda n: f'S{n:03d}')
    name = factory.Faker('city')
    city = factory.Faker('city')
    phone = factory.Faker('phone_number')
    email = factory.Faker('email')
    address = factory.Faker('address')
    is_active = True


class UserFactory(DjangoModelFactory):
    """Factory pour créer des utilisateurs de test."""
    
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.Faker('email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True
    password = factory.PostGenerationMethodCall('set_password', 'password123')
    role = 'membre'
    is_staff = False
    is_superuser = False


class MemberFactory(DjangoModelFactory):
    """Factory pour créer des membres de test."""
    
    class Meta:
        model = Member
    
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.Faker('email')
    phone = factory.Faker('phone_number')
    date_of_birth = factory.Faker('date_of_birth', minimum_age=18, maximum_age=80)
    gender = factory.Faker('bothify', letters='MF')
    address = factory.Faker('address')
    city = factory.Faker('city')
    postal_code = factory.Faker('postcode')
    status = 'actif'
    baptism_date = factory.Faker('date_between', start_date='-10y', end_date='today')
    is_baptized = True
    site = factory.SubFactory(SiteFactory)
    date_joined = factory.Faker('date_between', start_date='-5y', end_date='today')
    
    @factory.lazy_attribute
    def gender(self):
        return random.choice(['M', 'F'])


class EventCategoryFactory(DjangoModelFactory):
    """Factory pour créer les catégories d'événements."""
    
    class Meta:
        model = EventCategory
    
    name = factory.Sequence(lambda n: f'Catégorie {n}')


class EventFactory(DjangoModelFactory):
    """Factory pour créer des événements de test."""
    
    class Meta:
        model = Event
    
    title = factory.Faker('sentence', nb_words=4)
    description = factory.Faker('text')
    start_date = factory.Faker('date_between', start_date='today', end_date='+30d')
    end_date = factory.Faker('date_between', start_date='today', end_date='+30d')
    start_time = factory.Faker('time_object')
    location = factory.Faker('address')
    category = factory.SubFactory(EventCategoryFactory)
    site = factory.SubFactory(SiteFactory)
    visibility = 'members'
    all_day = False
    is_cancelled = False


class FinanceCategoryFactory(DjangoModelFactory):
    """Factory pour créer les catégories financières."""
    
    class Meta:
        model = FinanceCategory
    
    name = factory.Sequence(lambda n: f'Catégorie finance {n}')


class FinancialTransactionFactory(DjangoModelFactory):
    """Factory pour créer des transactions financières."""
    
    class Meta:
        model = FinancialTransaction
    
    transaction_date = factory.Faker('date_between', start_date='-1y', end_date='today')
    amount = factory.Faker('pydecimal', left_digits=5, right_digits=2, positive=True)
    status = 'en_attente'
    transaction_type = 'don'
    category = factory.SubFactory(FinanceCategoryFactory)
    site = factory.SubFactory(SiteFactory)
    description = factory.Faker('text', max_nb_chars=100)
    member = factory.SubFactory(MemberFactory)
    
    @factory.lazy_attribute
    def transaction_type(self):
        return random.choice(['don', 'dime', 'offrande', 'depense'])
