import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.finance.import_services import FinanceBundleImporter, SECTION_CHOICES


class Command(BaseCommand):
    help = 'Importe un bundle JSON de donnees coeur du module finance.'

    SECTION_CHOICES = SECTION_CHOICES

    def add_arguments(self, parser):
        parser.add_argument('input', help='Chemin du bundle JSON a importer.')
        parser.add_argument(
            '--sections',
            nargs='+',
            choices=self.SECTION_CHOICES,
            default=self.SECTION_CHOICES,
            help='Sections du bundle a importer.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simule l import sans conserver les modifications.',
        )

    def handle(self, *args, **options):
        input_path = Path(options['input'])
        sections = options['sections']
        dry_run = options['dry_run']

        if not input_path.exists():
            raise CommandError(f'Bundle introuvable: {input_path}')

        bundle = json.loads(input_path.read_text(encoding='utf-8'))
        importer = FinanceBundleImporter()

        try:
            result = importer.import_bundle(bundle, sections=sections, dry_run=dry_run)
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry-run: aucune modification n a ete conservee.'))

        for model_name in sorted(result['stats']):
            counters = result['stats'][model_name]
            self.stdout.write(
                f"{model_name}: {counters.get('created', 0)} cree(s), {counters.get('updated', 0)} mis a jour"
            )
        for warning in result['warnings']:
            self.stdout.write(self.style.WARNING(warning))