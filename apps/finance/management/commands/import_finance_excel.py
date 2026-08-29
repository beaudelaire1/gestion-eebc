from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.finance.import_services import FinanceBundleImporter, FinanceExcelWorkbookParser


class Command(BaseCommand):
    help = 'Importe un classeur Excel structure pour le module finance.'

    def add_arguments(self, parser):
        parser.add_argument('input', help='Chemin du fichier Excel a importer (.xlsx ou .xlsm).')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simule l import sans conserver les modifications.',
        )

    def handle(self, *args, **options):
        input_path = Path(options['input'])
        if not input_path.exists():
            raise CommandError(f'Fichier introuvable: {input_path}')

        parser = FinanceExcelWorkbookParser()
        importer = FinanceBundleImporter()

        try:
            bundle, sections = parser.parse(input_path)
            result = importer.import_bundle(bundle, sections=sections, dry_run=options['dry_run'])
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('Dry-run: aucune modification n a ete conservee.'))

        self.stdout.write(self.style.SUCCESS(f'Import Excel termine. Sections traitees: {", ".join(sections)}'))
        for model_name in sorted(result['stats']):
            counters = result['stats'][model_name]
            self.stdout.write(
                f"{model_name}: {counters.get('created', 0)} cree(s), {counters.get('updated', 0)} mis a jour"
            )
        for warning in result['warnings']:
            self.stdout.write(self.style.WARNING(warning))