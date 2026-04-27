"""
Pré-géocode les adresses de tous les membres pour remplir le cache DB.
Évite les appels API en temps réel lors du chargement de la carte.

Usage:
    python manage.py geocode_members
    python manage.py geocode_members --force   # Re-géocoder même si déjà en cache
"""
import time
import logging
from django.core.management.base import BaseCommand
from django.db.models import Q

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Pré-géocode les adresses des membres pour le cache DB'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Re-géocoder même si en cache')

    def handle(self, *args, **options):
        from apps.members.models import Member
        from apps.members.geocoding import geocode_address_with_metadata

        force = options['force']
        members = Member.objects.filter(
            Q(address__isnull=False) & ~Q(address='')
        ).select_related('family', 'site')

        total = members.count()
        geocoded = 0
        cached = 0
        failed = 0

        self.stdout.write(f'Géocodage de {total} membres...')

        for i, member in enumerate(members, 1):
            address = (member.address or '').strip()
            city = (member.city or '').strip()
            postal_code = (member.postal_code or '').strip()

            if not address and not city:
                continue

            try:
                result = geocode_address_with_metadata(
                    address=address,
                    city=city,
                    postal_code=postal_code,
                    force_refresh=force,
                )

                if result.get('from_cache'):
                    cached += 1
                elif result.get('coords'):
                    geocoded += 1
                    time.sleep(1.1)  # Respecter la limite Nominatim
                else:
                    failed += 1

                if i % 10 == 0:
                    self.stdout.write(f'  {i}/{total} traités...')

            except Exception as e:
                failed += 1
                logger.warning("Geocode failed for member %s: %s", member.id, e)

        self.stdout.write(self.style.SUCCESS(
            f'Terminé: {geocoded} géocodés, {cached} en cache, {failed} échoués sur {total}'
        ))
