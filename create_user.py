#!/usr/bin/env python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_eebc.settings')

import django
django.setup()

from apps.accounts.models import User

user, created = User.objects.get_or_create(
    username='schnader.janvier',
    defaults={
        'email': 'kimlegendre0@gmail.com',
        'first_name': 'Schnader',
        'last_name': 'JANVIER',
        'is_active': True,
    }
)

if created:
    user.set_password('eebc2024')
    user.save()
    print(f"✅ Utilisateur créé: {user.get_full_name()}")
    print(f"   Email: {user.email}")
    print(f"   Username: {user.username}")
    print(f"   Mot de passe: eebc2024")
else:
    print(f"ℹ️ Utilisateur existe déjà: {user.username}")
