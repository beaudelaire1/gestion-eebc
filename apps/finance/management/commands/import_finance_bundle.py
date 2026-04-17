import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_date, parse_datetime

from apps.accounts.models import User
from apps.core.models import Site
from apps.departments.models import Department
from apps.events.models import Event
from apps.finance.models import (
    Budget,
    BudgetCategory,
    BudgetForecast,
    BudgetItem,
    BudgetLine,
    BudgetRequest,
    FinanceCategory,
    FinancialTransaction,
    ForecastLine,
)
from apps.groups.models import Group
from apps.members.models import Member


class Command(BaseCommand):
    help = 'Importe un bundle JSON de donnees coeur du module finance.'

    SECTION_CHOICES = ['categories', 'budget_lines', 'budgets', 'forecasts', 'transactions']

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
        self.stats = {}
        self.warned = set()

        with transaction.atomic():
            if 'categories' in sections:
                self.import_finance_categories(bundle.get('finance_categories', []))
                self.import_budget_categories(bundle.get('budget_categories', []))

            if 'budget_lines' in sections:
                self.import_budget_lines(bundle.get('budget_lines', []))

            if 'budgets' in sections:
                self.import_budgets(bundle.get('budgets', []))
                self.import_budget_requests(bundle.get('budget_requests', []))

            if 'forecasts' in sections:
                self.import_forecasts(bundle.get('forecasts', []))

            if 'transactions' in sections:
                self.import_transactions(bundle.get('transactions', []))

            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING('Dry-run: aucune modification n a ete conservee.'))

        for model_name in sorted(self.stats):
            counters = self.stats[model_name]
            self.stdout.write(
                f"{model_name}: {counters.get('created', 0)} cree(s), {counters.get('updated', 0)} mis a jour"
            )

    def bump(self, model_name, action):
        self.stats.setdefault(model_name, {'created': 0, 'updated': 0})
        self.stats[model_name][action] += 1

    def warn_once(self, key, message):
        if key in self.warned:
            return
        self.warned.add(key)
        self.stdout.write(self.style.WARNING(message))

    def to_decimal(self, value):
        if value in (None, ''):
            return None
        return Decimal(str(value))

    def to_date(self, value):
        if not value:
            return None
        return parse_date(value)

    def to_datetime(self, value):
        if not value:
            return None
        return parse_datetime(value)

    def apply_values(self, obj, values):
        changed = False
        for field, value in values.items():
            if getattr(obj, field) != value:
                setattr(obj, field, value)
                changed = True
        if changed:
            obj.save()
        return changed

    def resolve_user(self, username):
        if not username:
            return None
        user = User.objects.filter(username=username).first()
        if user:
            return user
        self.warn_once(f'user:{username}', f'Utilisateur introuvable en prod: {username}. Valeur ignoree.')
        return None

    def resolve_site(self, site_name):
        if not site_name:
            return None
        sites = list(Site.objects.filter(name=site_name))
        if len(sites) == 1:
            return sites[0]
        if not sites:
            self.warn_once(f'site:{site_name}', f'Site introuvable en prod: {site_name}. Valeur ignoree.')
            return None
        self.warn_once(f'site_multi:{site_name}', f'Plusieurs sites nommes {site_name}. Premier enregistrement utilise.')
        return sites[0]

    def resolve_group(self, payload):
        if not payload:
            return None
        queryset = Group.objects.filter(name=payload['name'])
        site_name = payload.get('site_name')
        if site_name:
            queryset = queryset.filter(site__name=site_name)
        groups = list(queryset)
        if len(groups) == 1:
            return groups[0]
        if not groups:
            raise CommandError(f"Groupe introuvable pour le budget: {payload['name']}")
        raise CommandError(f"Groupe ambigu pour le budget: {payload['name']}")

    def resolve_department(self, payload):
        if not payload:
            return None
        queryset = Department.objects.filter(name=payload['name'])
        site_name = payload.get('site_name')
        if site_name:
            queryset = queryset.filter(site__name=site_name)
        departments = list(queryset)
        if len(departments) == 1:
            return departments[0]
        if not departments:
            raise CommandError(f"Departement introuvable pour le budget: {payload['name']}")
        raise CommandError(f"Departement ambigu pour le budget: {payload['name']}")

    def resolve_member(self, member_id):
        if not member_id:
            return None
        member = Member.objects.filter(member_id=member_id).first()
        if member:
            return member
        self.warn_once(f'member:{member_id}', f'Membre introuvable en prod: {member_id}. Valeur ignoree.')
        return None

    def resolve_event(self, payload):
        if not payload:
            return None
        queryset = Event.objects.filter(
            title=payload['title'],
            start_date=self.to_date(payload['start_date']),
        )
        site_name = payload.get('site_name')
        if site_name:
            queryset = queryset.filter(site__name=site_name)
        event = queryset.first()
        if event:
            return event
        self.warn_once(
            f"event:{payload['title']}:{payload['start_date']}",
            f"Evenement introuvable en prod: {payload['title']} ({payload['start_date']}). Valeur ignoree.",
        )
        return None

    def resolve_finance_category(self, name):
        if not name:
            return None
        category = FinanceCategory.objects.filter(name=name).first()
        if category:
            return category
        raise CommandError(f'Categorie financiere introuvable: {name}')

    def resolve_budget_category(self, name):
        if not name:
            return None
        category = BudgetCategory.objects.filter(name=name).first()
        if category:
            return category
        raise CommandError(f'Categorie de budget introuvable: {name}')

    def resolve_budget_item(self, payload):
        if not payload:
            return None
        group = self.resolve_group(payload.get('group')) if payload.get('group') else None
        department = self.resolve_department(payload.get('department')) if payload.get('department') else None
        category = self.resolve_budget_category(payload['category_name'])

        queryset = BudgetItem.objects.select_related('budget', 'category').filter(
            budget__year=payload['budget_year'],
            category=category,
        )
        if group:
            queryset = queryset.filter(budget__group=group)
        elif department:
            queryset = queryset.filter(budget__department=department)
        else:
            queryset = queryset.filter(budget__name=payload['budget_name'])
        item = queryset.first()
        if item:
            return item
        self.warn_once(
            f"budget_item:{payload['budget_name']}:{payload['category_name']}",
            f"Ligne de budget introuvable en prod pour transaction: {payload['budget_name']} / {payload['category_name']}",
        )
        return None

    def import_finance_categories(self, payloads):
        pending_parents = []
        for payload in payloads:
            obj, created = FinanceCategory.objects.get_or_create(
                name=payload['name'],
                defaults={
                    'description': payload.get('description', ''),
                    'is_income': payload.get('is_income', False),
                    'budget_annual': self.to_decimal(payload.get('budget_annual')),
                    'is_active': payload.get('is_active', True),
                },
            )
            if created:
                self.bump('FinanceCategory', 'created')
            elif self.apply_values(obj, {
                'description': payload.get('description', ''),
                'is_income': payload.get('is_income', False),
                'budget_annual': self.to_decimal(payload.get('budget_annual')),
                'is_active': payload.get('is_active', True),
            }):
                self.bump('FinanceCategory', 'updated')
            pending_parents.append((obj, payload.get('parent_name')))

        for obj, parent_name in pending_parents:
            parent = FinanceCategory.objects.filter(name=parent_name).first() if parent_name else None
            if obj.parent != parent:
                obj.parent = parent
                obj.save()

    def import_budget_categories(self, payloads):
        for payload in payloads:
            obj, created = BudgetCategory.objects.get_or_create(
                name=payload['name'],
                defaults={
                    'description': payload.get('description', ''),
                    'color': payload.get('color', '#0A36FF'),
                    'is_active': payload.get('is_active', True),
                },
            )
            if created:
                self.bump('BudgetCategory', 'created')
            elif self.apply_values(obj, {
                'description': payload.get('description', ''),
                'color': payload.get('color', '#0A36FF'),
                'is_active': payload.get('is_active', True),
            }):
                self.bump('BudgetCategory', 'updated')

    def import_budget_lines(self, payloads):
        for payload in payloads:
            category = self.resolve_finance_category(payload['category_name'])
            obj, created = BudgetLine.objects.get_or_create(
                category=category,
                year=payload['year'],
                month=payload.get('month'),
                defaults={
                    'planned_amount': self.to_decimal(payload['planned_amount']),
                    'notes': payload.get('notes', ''),
                },
            )
            if created:
                self.bump('BudgetLine', 'created')
            elif self.apply_values(obj, {
                'planned_amount': self.to_decimal(payload['planned_amount']),
                'notes': payload.get('notes', ''),
            }):
                self.bump('BudgetLine', 'updated')

    def import_budgets(self, payloads):
        for payload in payloads:
            group = self.resolve_group(payload.get('group')) if payload.get('group') else None
            department = self.resolve_department(payload.get('department')) if payload.get('department') else None
            defaults = {
                'name': payload['name'],
                'total_requested': self.to_decimal(payload['total_requested']),
                'total_approved': self.to_decimal(payload['total_approved']),
                'status': payload['status'],
                'created_by': self.resolve_user(payload.get('created_by')),
                'approved_by': self.resolve_user(payload.get('approved_by')),
                'submitted_at': self.to_datetime(payload.get('submitted_at')),
                'approved_at': self.to_datetime(payload.get('approved_at')),
                'description': payload.get('description', ''),
                'approval_notes': payload.get('approval_notes', ''),
            }

            if group:
                budget, created = Budget.objects.get_or_create(year=payload['year'], group=group, defaults=defaults)
            elif department:
                budget, created = Budget.objects.get_or_create(year=payload['year'], department=department, defaults=defaults)
            else:
                budget = Budget.objects.filter(
                    year=payload['year'],
                    name=payload['name'],
                    group=None,
                    department=None,
                ).first()
                created = budget is None
                if created:
                    budget = Budget.objects.create(year=payload['year'], group=None, department=None, **defaults)

            if created:
                self.bump('Budget', 'created')
            else:
                values = defaults | {'name': payload['name']}
                if self.apply_values(budget, values):
                    self.bump('Budget', 'updated')

            for item_payload in payload.get('items', []):
                category = self.resolve_budget_category(item_payload['category_name'])
                item_defaults = {
                    'requested_amount': self.to_decimal(item_payload['requested_amount']),
                    'approved_amount': self.to_decimal(item_payload['approved_amount']),
                    'approval_status': item_payload.get('approval_status', BudgetItem.ApprovalStatus.PENDING),
                    'approved_by': self.resolve_user(item_payload.get('approved_by')),
                    'approved_at': self.to_datetime(item_payload.get('approved_at')),
                    'approval_comments': item_payload.get('approval_comments', ''),
                    'rejection_reason': item_payload.get('rejection_reason', ''),
                    'description': item_payload.get('description', ''),
                    'justification': item_payload.get('justification', ''),
                    'priority': item_payload.get('priority', 1),
                }
                item, item_created = BudgetItem.objects.get_or_create(
                    budget=budget,
                    category=category,
                    defaults=item_defaults,
                )
                if item_created:
                    self.bump('BudgetItem', 'created')
                elif self.apply_values(item, item_defaults):
                    self.bump('BudgetItem', 'updated')

    def import_budget_requests(self, payloads):
        for payload in payloads:
            category = self.resolve_budget_category(payload['category_name'])
            group = self.resolve_group(payload.get('group')) if payload.get('group') else None
            department = self.resolve_department(payload.get('department')) if payload.get('department') else None
            defaults = {
                'description': payload['description'],
                'approved_amount': self.to_decimal(payload['approved_amount']),
                'urgency': payload['urgency'],
                'needed_by': self.to_date(payload.get('needed_by')),
                'status': payload['status'],
                'requested_by': self.resolve_user(payload.get('requested_by')),
                'reviewed_by': self.resolve_user(payload.get('reviewed_by')),
                'reviewed_at': self.to_datetime(payload.get('reviewed_at')),
                'justification': payload['justification'],
                'review_notes': payload.get('review_notes', ''),
            }
            obj, created = BudgetRequest.objects.get_or_create(
                title=payload['title'],
                requested_amount=self.to_decimal(payload['requested_amount']),
                category=category,
                group=group,
                department=department,
                defaults=defaults,
            )
            if created:
                self.bump('BudgetRequest', 'created')
            elif self.apply_values(obj, defaults | {'title': payload['title']}):
                self.bump('BudgetRequest', 'updated')

    def import_forecasts(self, payloads):
        for payload in payloads:
            forecast, created = BudgetForecast.objects.get_or_create(
                year=payload['year'],
                scenario=payload['scenario'],
                defaults={
                    'name': payload['name'],
                    'description': payload.get('description', ''),
                    'is_active': payload.get('is_active', True),
                    'created_by': self.resolve_user(payload.get('created_by')),
                },
            )
            if created:
                self.bump('BudgetForecast', 'created')
            elif self.apply_values(forecast, {
                'name': payload['name'],
                'description': payload.get('description', ''),
                'is_active': payload.get('is_active', True),
                'created_by': self.resolve_user(payload.get('created_by')),
            }):
                self.bump('BudgetForecast', 'updated')

            forecast.lines.all().delete()
            for line_payload in payload.get('lines', []):
                ForecastLine.objects.create(
                    forecast=forecast,
                    label=line_payload['label'],
                    line_type=line_payload['line_type'],
                    category=self.resolve_finance_category(line_payload.get('category_name')) if line_payload.get('category_name') else None,
                    jan=self.to_decimal(line_payload.get('jan')) or Decimal('0'),
                    feb=self.to_decimal(line_payload.get('feb')) or Decimal('0'),
                    mar=self.to_decimal(line_payload.get('mar')) or Decimal('0'),
                    apr=self.to_decimal(line_payload.get('apr')) or Decimal('0'),
                    may=self.to_decimal(line_payload.get('may')) or Decimal('0'),
                    jun=self.to_decimal(line_payload.get('jun')) or Decimal('0'),
                    jul=self.to_decimal(line_payload.get('jul')) or Decimal('0'),
                    aug=self.to_decimal(line_payload.get('aug')) or Decimal('0'),
                    sep=self.to_decimal(line_payload.get('sep')) or Decimal('0'),
                    oct=self.to_decimal(line_payload.get('oct')) or Decimal('0'),
                    nov=self.to_decimal(line_payload.get('nov')) or Decimal('0'),
                    dec=self.to_decimal(line_payload.get('dec')) or Decimal('0'),
                    notes=line_payload.get('notes', ''),
                )
                self.bump('ForecastLine', 'created')

    def import_transactions(self, payloads):
        for payload in payloads:
            defaults = {
                'site': self.resolve_site(payload.get('site_name')),
                'amount': self.to_decimal(payload['amount']),
                'transaction_type': payload['transaction_type'],
                'payment_method': payload['payment_method'],
                'status': payload['status'],
                'transaction_date': self.to_date(payload['transaction_date']),
                'description': payload.get('description', ''),
                'category': self.resolve_finance_category(payload.get('category_name')) if payload.get('category_name') else None,
                'member': self.resolve_member(payload.get('member_id')),
                'event': self.resolve_event(payload.get('event')),
                'budget_item': self.resolve_budget_item(payload.get('budget_item')),
                'recorded_by': self.resolve_user(payload.get('recorded_by')),
                'validated_by': self.resolve_user(payload.get('validated_by')),
                'validated_at': self.to_datetime(payload.get('validated_at')),
                'notes': payload.get('notes', ''),
                'is_deleted': payload.get('is_deleted', False),
                'deleted_at': self.to_datetime(payload.get('deleted_at')),
                'deleted_by': self.resolve_user(payload.get('deleted_by')),
            }
            obj, created = FinancialTransaction.all_objects.get_or_create(
                reference=payload['reference'],
                defaults=defaults,
            )
            if created:
                self.bump('FinancialTransaction', 'created')
            elif self.apply_values(obj, defaults):
                self.bump('FinancialTransaction', 'updated')