import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.finance.models import (
    Budget,
    BudgetCategory,
    BudgetForecast,
    BudgetItem,
    BudgetLine,
    BudgetRequest,
    FinanceCategory,
    FinancialTransaction,
)


def serialize_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def serialize_group(group):
    if not group:
        return None
    return {
        'name': group.name,
        'site_name': group.site.name if group.site else None,
    }


def serialize_department(department):
    if not department:
        return None
    return {
        'name': department.name,
        'site_name': department.site.name if department.site else None,
    }


def serialize_budget_item_ref(budget_item):
    if not budget_item:
        return None
    budget = budget_item.budget
    return {
        'budget_name': budget.name,
        'budget_year': budget.year,
        'group': serialize_group(budget.group),
        'department': serialize_department(budget.department),
        'category_name': budget_item.category.name,
    }


class Command(BaseCommand):
    help = 'Exporte les donnees coeur du module finance dans un bundle JSON.'

    SECTION_CHOICES = ['categories', 'budget_lines', 'budgets', 'forecasts', 'transactions']

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            help='Chemin du fichier JSON a produire.',
        )
        parser.add_argument(
            '--sections',
            nargs='+',
            choices=self.SECTION_CHOICES,
            default=self.SECTION_CHOICES,
            help='Sections a inclure dans le bundle.',
        )

    def handle(self, *args, **options):
        sections = options['sections']
        output = options.get('output')

        if output:
            output_path = Path(output)
        else:
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            output_path = Path('backups') / f'finance_bundle_{timestamp}.json'

        output_path.parent.mkdir(parents=True, exist_ok=True)

        bundle = {
            'meta': {
                'exported_at': timezone.now().isoformat(),
                'source_database': 'local',
                'sections': sections,
                'schema_version': 1,
            }
        }

        if 'categories' in sections:
            bundle['finance_categories'] = self.export_finance_categories()
            bundle['budget_categories'] = self.export_budget_categories()

        if 'budget_lines' in sections:
            bundle['budget_lines'] = self.export_budget_lines()

        if 'budgets' in sections:
            bundle['budgets'] = self.export_budgets()
            bundle['budget_requests'] = self.export_budget_requests()

        if 'forecasts' in sections:
            bundle['forecasts'] = self.export_forecasts()

        if 'transactions' in sections:
            bundle['transactions'] = self.export_transactions()

        bundle['meta']['counts'] = {
            key: len(value)
            for key, value in bundle.items()
            if isinstance(value, list)
        }

        output_path.write_text(
            json.dumps(bundle, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

        self.stdout.write(self.style.SUCCESS(f'Bundle finance cree: {output_path}'))
        for key, count in bundle['meta']['counts'].items():
            self.stdout.write(f' - {key}: {count}')

    def export_finance_categories(self):
        categories = []
        queryset = FinanceCategory.objects.select_related('parent').order_by('name', 'pk')
        for category in queryset:
            categories.append({
                'name': category.name,
                'description': category.description,
                'is_income': category.is_income,
                'budget_annual': serialize_value(category.budget_annual),
                'parent_name': category.parent.name if category.parent else None,
                'is_active': category.is_active,
            })
        return categories

    def export_budget_categories(self):
        categories = []
        queryset = BudgetCategory.objects.order_by('name', 'pk')
        for category in queryset:
            categories.append({
                'name': category.name,
                'description': category.description,
                'color': category.color,
                'is_active': category.is_active,
            })
        return categories

    def export_budget_lines(self):
        lines = []
        queryset = BudgetLine.objects.select_related('category').order_by('year', 'month', 'category__name', 'pk')
        for line in queryset:
            lines.append({
                'category_name': line.category.name,
                'year': line.year,
                'month': line.month,
                'planned_amount': serialize_value(line.planned_amount),
                'notes': line.notes,
            })
        return lines

    def export_budgets(self):
        budgets = []
        queryset = Budget.objects.select_related(
            'group__site',
            'department__site',
            'created_by',
            'approved_by',
        ).prefetch_related('items__category', 'items__approved_by').order_by('year', 'name', 'pk')

        for budget in queryset:
            items = []
            for item in budget.items.all():
                items.append({
                    'category_name': item.category.name,
                    'requested_amount': serialize_value(item.requested_amount),
                    'approved_amount': serialize_value(item.approved_amount),
                    'approval_status': item.approval_status,
                    'approved_by': item.approved_by.username if item.approved_by else None,
                    'approved_at': serialize_value(item.approved_at),
                    'approval_comments': item.approval_comments,
                    'rejection_reason': item.rejection_reason,
                    'description': item.description,
                    'justification': item.justification,
                    'priority': item.priority,
                })

            budgets.append({
                'name': budget.name,
                'year': budget.year,
                'group': serialize_group(budget.group),
                'department': serialize_department(budget.department),
                'total_requested': serialize_value(budget.total_requested),
                'total_approved': serialize_value(budget.total_approved),
                'status': budget.status,
                'created_by': budget.created_by.username if budget.created_by else None,
                'approved_by': budget.approved_by.username if budget.approved_by else None,
                'submitted_at': serialize_value(budget.submitted_at),
                'approved_at': serialize_value(budget.approved_at),
                'description': budget.description,
                'approval_notes': budget.approval_notes,
                'items': items,
            })
        return budgets

    def export_budget_requests(self):
        requests_data = []
        queryset = BudgetRequest.objects.select_related(
            'category',
            'group__site',
            'department__site',
            'requested_by',
            'reviewed_by',
        ).order_by('created_at', 'pk')

        for request_obj in queryset:
            requests_data.append({
                'title': request_obj.title,
                'description': request_obj.description,
                'requested_amount': serialize_value(request_obj.requested_amount),
                'approved_amount': serialize_value(request_obj.approved_amount),
                'category_name': request_obj.category.name,
                'group': serialize_group(request_obj.group),
                'department': serialize_department(request_obj.department),
                'urgency': request_obj.urgency,
                'needed_by': serialize_value(request_obj.needed_by),
                'status': request_obj.status,
                'requested_by': request_obj.requested_by.username if request_obj.requested_by else None,
                'reviewed_by': request_obj.reviewed_by.username if request_obj.reviewed_by else None,
                'reviewed_at': serialize_value(request_obj.reviewed_at),
                'justification': request_obj.justification,
                'review_notes': request_obj.review_notes,
            })
        return requests_data

    def export_forecasts(self):
        forecasts = []
        queryset = BudgetForecast.objects.select_related('created_by').prefetch_related('lines__category').order_by('year', 'scenario', 'pk')
        for forecast in queryset:
            lines = []
            for line in forecast.lines.all():
                lines.append({
                    'label': line.label,
                    'line_type': line.line_type,
                    'category_name': line.category.name if line.category else None,
                    'jan': serialize_value(line.jan),
                    'feb': serialize_value(line.feb),
                    'mar': serialize_value(line.mar),
                    'apr': serialize_value(line.apr),
                    'may': serialize_value(line.may),
                    'jun': serialize_value(line.jun),
                    'jul': serialize_value(line.jul),
                    'aug': serialize_value(line.aug),
                    'sep': serialize_value(line.sep),
                    'oct': serialize_value(line.oct),
                    'nov': serialize_value(line.nov),
                    'dec': serialize_value(line.dec),
                    'notes': line.notes,
                })

            forecasts.append({
                'name': forecast.name,
                'year': forecast.year,
                'scenario': forecast.scenario,
                'description': forecast.description,
                'is_active': forecast.is_active,
                'created_by': forecast.created_by.username if forecast.created_by else None,
                'lines': lines,
            })
        return forecasts

    def export_transactions(self):
        transactions = []
        queryset = FinancialTransaction.all_objects.select_related(
            'site',
            'category',
            'member',
            'event__site',
            'budget_item__budget__group__site',
            'budget_item__budget__department__site',
            'budget_item__category',
            'recorded_by',
            'validated_by',
            'deleted_by',
        ).order_by('transaction_date', 'reference')

        for transaction in queryset:
            transactions.append({
                'reference': transaction.reference,
                'site_name': transaction.site.name if transaction.site else None,
                'amount': serialize_value(transaction.amount),
                'transaction_type': transaction.transaction_type,
                'payment_method': transaction.payment_method,
                'status': transaction.status,
                'transaction_date': serialize_value(transaction.transaction_date),
                'description': transaction.description,
                'category_name': transaction.category.name if transaction.category else None,
                'member_id': transaction.member.member_id if transaction.member else None,
                'event': {
                    'title': transaction.event.title,
                    'start_date': serialize_value(transaction.event.start_date),
                    'site_name': transaction.event.site.name if transaction.event and transaction.event.site else None,
                } if transaction.event else None,
                'budget_item': serialize_budget_item_ref(transaction.budget_item),
                'recorded_by': transaction.recorded_by.username if transaction.recorded_by else None,
                'validated_by': transaction.validated_by.username if transaction.validated_by else None,
                'validated_at': serialize_value(transaction.validated_at),
                'notes': transaction.notes,
                'is_deleted': transaction.is_deleted,
                'deleted_at': serialize_value(transaction.deleted_at),
                'deleted_by': transaction.deleted_by.username if transaction.deleted_by else None,
            })
        return transactions