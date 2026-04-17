from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Importe les prévisionnels 2025 EEBC avec lecture UTF-8 sûre"

    def handle(self, *args, **options):
        script_path = Path(__file__).resolve().parents[2] / 'import_bilan_2025_complet.py'
        namespace = {'__name__': '__main__'}
        exec(script_path.read_text(encoding='utf-8'), namespace)
        self.stdout.write(self.style.SUCCESS('Import des prévisionnels 2025 terminé.'))