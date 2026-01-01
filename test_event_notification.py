#!/usr/bin/env python
"""Test de notification lors de création d'événement."""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_eebc.settings')

import django
django.setup()

from apps.events.models import Event
from datetime import date, timedelta

print("Création d'un événement test...")

event = Event.objects.create(
    title='Test Notification Email',
    description='Ceci est un test de notification automatique',
    start_date=date.today() + timedelta(days=7),
    location='Église EEBC',
    notification_scope='all'
)

print(f"✅ Événement créé: {event.title}")
print(f"   ID: {event.id}")
print(f"   Scope: {event.notification_scope}")
print(f"   Date: {event.start_date}")

# Vérifier les logs d'emails
from apps.communication.models import EmailLog
recent_logs = EmailLog.objects.order_by('-created_at')[:5]
print(f"\n📧 Derniers emails envoyés:")
for log in recent_logs:
    print(f"   - {log.subject} → {log.recipient_email} [{log.status}]")

# Nettoyer
# event.delete()
# print("\n🗑️ Événement supprimé")
