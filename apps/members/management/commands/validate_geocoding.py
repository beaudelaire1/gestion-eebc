"""
Django management command : Valider et déboguer le géocodage.

Usage:
    python manage.py validate_geocoding
    python manage.py validate_geocoding --address "12 rue Test" --city "Cayenne"
    python manage.py validate_geocoding --address "12 rue Test" --city "Cayenne" --verbose
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from decimal import Decimal

from apps.members.geocoding import (
    geocode_address_with_metadata,
    build_canonical_address,
    normalize_address_component,
    GeocodedAddress,
)
from apps.core.models import City, Site
from apps.members.models import Member


class Command(BaseCommand):
    help = "Valider et déboguer le géocodage des adresses"

    def add_arguments(self, parser):
        parser.add_argument(
            "--address",
            type=str,
            help="Adresse à tester",
            default="Place Grenoble",
        )
        parser.add_argument(
            "--city",
            type=str,
            help="Ville",
            default="Cayenne",
        )
        parser.add_argument(
            "--postal-code",
            type=str,
            help="Code postal",
            default="97300",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Mode verbeux",
        )
        parser.add_argument(
            "--all-members",
            action="store_true",
            help="Valider tous les membres",
        )
        parser.add_argument(
            "--check-cache",
            action="store_true",
            help="Vérifier l'état du cache",
        )
        parser.add_argument(
            "--clear-cache",
            action="store_true",
            help="Vider le cache (danger!)",
        )

    def handle(self, *args, **options):
        if options["clear_cache"]:
            self.handle_clear_cache()
            return

        if options["check_cache"]:
            self.handle_check_cache()
            return

        if options["all_members"]:
            self.handle_validate_all_members(options["verbose"])
            return

        # Test single address
        self.handle_test_address(
            options["address"],
            options["city"],
            options["postal_code"],
            options["verbose"],
        )

    def handle_test_address(self, address, city, postal_code, verbose):
        """Tester une seule adresse."""
        self.stdout.write(f"\n{'=' * 70}")
        self.stdout.write(f"GÉOCODAGE TEST")
        self.stdout.write(f"{'=' * 70}")

        self.stdout.write(f"\n📍 Adresse: {address}")
        self.stdout.write(f"   Ville: {city}")
        self.stdout.write(f"   CP: {postal_code}")

        # Normalisation
        canonical = build_canonical_address(address, city, postal_code)
        self.stdout.write(f"\n📋 Normalisation:")
        self.stdout.write(f"   Query: {canonical['query']}")
        self.stdout.write(f"   Key: {canonical['address_key'][:16]}...")

        # Check cache
        cached = GeocodedAddress.objects.filter(
            address_key=canonical["address_key"]
        ).first()

        if cached:
            self.stdout.write(f"\n💾 Cache: FOUND")
            self.stdout.write(f"   Lat: {cached.latitude}")
            self.stdout.write(f"   Lon: {cached.longitude}")
            self.stdout.write(f"   Provider: {cached.provider}")
            if cached.expires_at:
                expired = cached.expires_at < timezone.now()
                status = "EXPIRED ❌" if expired else "VALID ✅"
                self.stdout.write(f"   Status: {status}")
        else:
            self.stdout.write(f"\n💾 Cache: NOT FOUND")

        # Geocode
        self.stdout.write(f"\n🔄 Géocodage...")
        result = geocode_address_with_metadata(address, city, postal_code)

        if result["coords"]:
            lat, lon = result["coords"]
            self.stdout.write(f"   ✅ SUCCESS")
            self.stdout.write(f"   Lat: {lat}")
            self.stdout.write(f"   Lon: {lon}")
            self.stdout.write(f"   Provider: {result['provider']}")
            self.stdout.write(f"   From Cache: {result['from_cache']}")

            # Validation bounds
            if 1.0 <= lat <= 8.5 and -54.5 <= lon <= -50.5:
                self.stdout.write(f"   Bounds: ✅ VALID (Guyane)")
            else:
                self.stdout.write(
                    self.style.ERROR(f"   Bounds: ❌ INVALID (Lat:{lat}, Lon:{lon})")
                )

            if verbose:
                # Afficher sur Google Maps
                maps_url = f"https://www.google.com/maps/@{lat},{lon},15z"
                self.stdout.write(f"\n📍 Google Maps: {maps_url}")
        else:
            self.stdout.write(self.style.ERROR(f"   ❌ FAILED"))
            self.stdout.write(f"   Provider: {result['provider']}")

        self.stdout.write(f"\n{'=' * 70}\n")

    def handle_validate_all_members(self, verbose):
        """Valider tous les membres."""
        self.stdout.write("\n🔍 Validation tous les membres...")

        members = Member.objects.filter(address__isnull=False).exclude(address="")
        total = members.count()

        valid = 0
        invalid = 0
        invalid_members = []

        for member in members:
            result = geocode_address_with_metadata(
                address=member.address,
                city=member.city or "",
                postal_code=member.postal_code or "",
            )

            if result["coords"]:
                lat, lon = result["coords"]
                # Check bounds
                if 1.0 <= lat <= 8.5 and -54.5 <= lon <= -50.5:
                    valid += 1
                else:
                    invalid += 1
                    invalid_members.append(
                        {
                            "id": member.id,
                            "name": member.name,
                            "address": member.address,
                            "lat": lat,
                            "lon": lon,
                        }
                    )
            else:
                invalid += 1
                invalid_members.append(
                    {
                        "id": member.id,
                        "name": member.name,
                        "address": member.address,
                        "reason": "No coordinates",
                    }
                )

        self.stdout.write(f"\n📊 Résultats:")
        self.stdout.write(f"   Total: {total}")
        self.stdout.write(f"   ✅ Valid: {valid} ({100*valid/total:.1f}%)")
        self.stdout.write(f"   ❌ Invalid: {invalid}")

        if invalid_members:
            self.stdout.write(f"\n⚠️  Membres invalides:")
            for m in invalid_members[:20]:  # Top 20
                reason = m.get("reason") or f"({m['lat']}, {m['lon']})"
                self.stdout.write(f"   - {m['name']} (#{m['id']}): {reason}")

            if len(invalid_members) > 20:
                self.stdout.write(f"   ... et {len(invalid_members)-20} autres")

        self.stdout.write()

    def handle_check_cache(self):
        """Vérifier l'état du cache."""
        self.stdout.write("\n💾 Cache Status:")

        total = GeocodedAddress.objects.count()
        valid = GeocodedAddress.objects.filter(
            latitude__gte=Decimal("1.0"),
            latitude__lte=Decimal("8.5"),
            longitude__gte=Decimal("-54.5"),
            longitude__lte=Decimal("-50.5"),
        ).count()

        invalid = GeocodedAddress.objects.filter(
            latitude__lt=Decimal("1.0"),
        ) | GeocodedAddress.objects.filter(longitude__lt=Decimal("-54.5"))
        invalid_count = invalid.count()

        expired = GeocodedAddress.objects.filter(
            expires_at__lt=timezone.now()
        ).count()

        self.stdout.write(f"   Total entries: {total}")
        self.stdout.write(f"   ✅ Valid: {valid}")
        self.stdout.write(
            self.style.ERROR(f"   ❌ Invalid (out of bounds): {invalid_count}")
        )
        self.stdout.write(f"   ⏰ Expired: {expired}")
        self.stdout.write()

    def handle_clear_cache(self):
        """Vider le cache (DANGER)."""
        if not self.confirm("Êtes-vous SÛR de vouloir vider le cache?"):
            self.stdout.write("Annulé.")
            return

        count = GeocodedAddress.objects.count()
        GeocodedAddress.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"✅ {count} entrées supprimées"))

    def confirm(self, message):
        """Demander confirmation."""
        response = input(f"\n{message} (y/N): ")
        return response.lower() == "y"
