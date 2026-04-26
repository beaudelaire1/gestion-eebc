"""Vues pour le module Finance."""

import logging
from pathlib import Path

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from datetime import date, timedelta
from decimal import Decimal

from .models import FinancialTransaction, FinanceCategory, ReceiptProof, BudgetLine, BudgetCategory, Budget, BudgetItem, BudgetRequest
from .forms import TransactionForm, ProofUploadForm, FinanceCategoryForm, FinanceExcelImportForm, DonationReceiptForm
from .import_services import (
    FINANCE_IMPORT_SHEET_SPECS,
    FinanceBundleImporter,
    FinanceExcelWorkbookParser,
    FinanceImportError,
    build_finance_import_template_workbook,
)
from .services import TransactionService, BudgetService, DEDICATED_FUNDS_PARENT
from apps.core.permissions import role_required

logger = logging.getLogger(__name__)


@login_required
@role_required('admin', 'finance')
def dashboard(request):
    """
    Tableau de bord financier.
    
    Utilise TransactionService pour récupérer les statistiques.
    Requirements: 7.2, 21.1
    """
    available_years = list(
        FinancialTransaction.objects.filter(status=FinancialTransaction.Status.VALIDE)
        .dates('transaction_date', 'year', order='DESC')
    )
    available_year_values = [year.year for year in available_years]

    year_param = request.GET.get('year', '').strip()
    if year_param.isdigit():
        selected_year = int(year_param)
    elif available_year_values:
        selected_year = available_year_values[0]
    else:
        selected_year = date.today().year

    # Déléguer la logique métier au service
    stats = TransactionService.get_dashboard_stats(year=selected_year)
    
    # Données pour le graphique d'évolution des dons (12 mois)
    donations_chart_data = TransactionService.get_monthly_donations_data(12, year=selected_year)
    
    # Données pour le graphique de répartition des dépenses (12 mois)
    expenses_chart_data = TransactionService.get_expenses_distribution_data(12, year=selected_year)
    
    context = {
        'month_income': stats['month_income'],
        'month_expenses': stats['month_expenses'],
        'month_balance': stats['month_balance'],
        'month_dedicated_funds': stats['month_dedicated_funds'],
        'year_income': stats['year_income'],
        'year_expenses': stats['year_expenses'],
        'year_balance': stats['year_balance'],
        'dedicated_funds_total': stats['dedicated_funds_total'],
        'closing_balance': stats['closing_balance'],
        'income_summary': stats['income_summary'],
        'expense_summary': stats['expense_summary'],
        'dedicated_funds_summary': stats['dedicated_funds_summary'],
        'recent_transactions': stats['recent_transactions'],
        'pending_count': stats['pending_count'],
        'donations_chart_data': donations_chart_data,
        'expenses_chart_data': expenses_chart_data,
        'available_years': available_year_values,
        'selected_year': selected_year,
        'reference_date': stats['reference_date'],
        'current_year': date.today().year,
    }
    
    return render(request, 'finance/dashboard.html', context)


@login_required
@role_required('admin', 'finance')
def dashboard_chart_data(request):
    """
    API endpoint pour les données de graphiques du dashboard.
    
    Requirements: 21.1, 21.2, 21.4
    """
    months = int(request.GET.get('months', 12))
    chart_type = request.GET.get('type', 'donations')
    year_param = request.GET.get('year', '').strip()
    selected_year = int(year_param) if year_param.isdigit() else None
    
    # Limiter le nombre de mois pour éviter les abus
    if months not in [3, 6, 12, 24]:
        months = 12
    
    # Récupérer les données via le service selon le type
    if chart_type == 'expenses':
        chart_data = TransactionService.get_expenses_distribution_data(months, year=selected_year)
    else:  # donations par défaut
        chart_data = TransactionService.get_monthly_donations_data(months, year=selected_year)
    
    return JsonResponse(chart_data)


@login_required
@role_required('admin', 'finance')
def transaction_list(request):
    """Liste des transactions avec filtres."""
    transactions = FinancialTransaction.objects.select_related(
        'category', 'member', 'recorded_by'
    )
    
    # Filtres
    transaction_type = request.GET.get('type')
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    if status:
        transactions = transactions.filter(status=status)
    if date_from:
        transactions = transactions.filter(transaction_date__gte=date_from)
    if date_to:
        transactions = transactions.filter(transaction_date__lte=date_to)
    
    # Tri
    sort_by = request.GET.get('sort', 'transaction_date')
    sort_order = request.GET.get('order', 'desc')
    
    # Champs de tri autorisés
    allowed_sort_fields = ['transaction_date', 'reference', 'amount', 'status', 'transaction_type']
    if sort_by not in allowed_sort_fields:
        sort_by = 'transaction_date'
    
    # Appliquer le tri
    if sort_order == 'desc':
        sort_by = f'-{sort_by}'
    
    transactions = transactions.order_by(sort_by)
    
    paginator = Paginator(transactions, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    
    context = {
        'transactions': page_obj,
        'page_obj': page_obj,
        'transaction_types': FinancialTransaction.TransactionType.choices,
        'statuses': FinancialTransaction.Status.choices,
        'current_sort': request.GET.get('sort', 'transaction_date'),
        'current_order': request.GET.get('order', 'desc'),
    }
    
    if request.htmx:
        return render(request, 'finance/partials/transaction_list_content.html', context)
    return render(request, 'finance/transaction_list.html', context)


@login_required
@role_required('admin', 'finance')
def transaction_create(request):
    """
    Créer une nouvelle transaction.
    
    Utilise TransactionService pour la création.
    Requirements: 7.2
    """
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            # Déléguer la création au service
            result = TransactionService.create_transaction(
                data=form.cleaned_data,
                recorded_by=request.user
            )
            
            if result.success:
                transaction = result.data['transaction']
                messages.success(request, f"Transaction {transaction.reference} créée.")
                return redirect('finance:transaction_detail', pk=transaction.pk)
            else:
                messages.error(request, result.error)
    else:
        initial = {}
        if request.GET.get('type'):
            initial['transaction_type'] = request.GET['type']
        form = TransactionForm(initial=initial)
    
    return render(request, 'finance/transaction_form.html', {'form': form})


@login_required
@role_required('admin', 'finance')
def transaction_detail(request, pk):
    """Détail d'une transaction."""
    transaction = get_object_or_404(
        FinancialTransaction.objects.select_related('category', 'member'),
        pk=pk
    )
    proofs = transaction.proofs.all()
    
    context = {
        'transaction': transaction,
        'proofs': proofs,
        'proof_form': ProofUploadForm(),
    }
    
    return render(request, 'finance/transaction_detail.html', context)


@login_required
@role_required('admin', 'finance')
def transaction_validate(request, pk):
    """
    Valider une transaction.
    
    Utilise TransactionService pour la validation.
    Requirements: 7.2
    """
    transaction = get_object_or_404(FinancialTransaction, pk=pk)
    
    # Déléguer la validation au service
    result = TransactionService.validate_transaction(
        transaction=transaction,
        validated_by=request.user
    )
    
    if result.success:
        messages.success(request, f"Transaction {transaction.reference} validée.")
    else:
        messages.error(request, result.error)
    
    return redirect('finance:transaction_detail', pk=pk)


@login_required
@role_required('admin', 'finance')
def transaction_receipt_pdf(request, pk):
    """Génère un reçu PDF pour une transaction manuelle (don, dîme, offrande)."""
    transaction = get_object_or_404(FinancialTransaction, pk=pk)

    income_types = ('don', 'dime', 'offrande')
    if transaction.transaction_type not in income_types:
        messages.error(request, "Seuls les dons, dîmes et offrandes peuvent avoir un reçu.")
        return redirect('finance:transaction_detail', pk=pk)

    from .pdf_service import generate_transaction_receipt_pdf
    pdf_bytes, receipt_number = generate_transaction_receipt_pdf(transaction)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="recu_{receipt_number}.pdf"'
    return response


@login_required
@role_required('admin', 'finance')
def donation_receipt_create(request):
    """Page de création d'un reçu de don avec formulaire (espèces, chèque…)."""
    if request.method == 'POST':
        form = DonationReceiptForm(request.POST)
        if form.is_valid():
            from .pdf_service import generate_manual_donation_receipt_pdf

            pdf_bytes, receipt_number = generate_manual_donation_receipt_pdf(
                donor_name=form.cleaned_data['donor_name'],
                donor_address=form.cleaned_data.get('donor_address', ''),
                donor_email=form.cleaned_data.get('donor_email', ''),
                amount=form.cleaned_data['amount'],
                donation_type=form.cleaned_data['donation_type'],
                payment_method=form.cleaned_data['payment_method'],
                donation_date=form.cleaned_data['donation_date'],
            )

            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="recu_{receipt_number}.pdf"'
            return response
    else:
        form = DonationReceiptForm(initial={'donation_date': date.today()})

    return render(request, 'finance/donation_receipt_create.html', {'form': form})


@login_required
@role_required('admin', 'finance')
def member_info_api(request, pk):
    """API JSON pour pré-remplir le formulaire de reçu depuis un membre."""
    from apps.members.models import Member
    member = get_object_or_404(Member, pk=pk)
    address_parts = [member.address or '']
    city_line = ' '.join(filter(None, [member.postal_code, member.city]))
    if city_line:
        address_parts.append(city_line)
    return JsonResponse({
        'name': member.get_full_name(),
        'email': member.email or '',
        'address': ', '.join(p for p in address_parts if p.strip()),
    })


@login_required
@role_required('admin', 'finance')
def proof_upload(request, pk):
    """Upload d'une preuve de paiement."""
    transaction = get_object_or_404(FinancialTransaction, pk=pk)
    
    if request.method == 'POST':
        form = ProofUploadForm(request.POST, request.FILES)
        if form.is_valid():
            proof = form.save(commit=False)
            proof.transaction = transaction
            proof.uploaded_by = request.user
            proof.save()
            messages.success(request, "Justificatif ajouté.")
    
    return redirect('finance:transaction_detail', pk=pk)


@login_required
@role_required('admin', 'finance')
def budget_overview(request):
    """Vue d'ensemble du budget."""
    year = int(request.GET.get('year', date.today().year))
    
    budget_lines = BudgetLine.objects.filter(year=year).select_related('category')
    categories = FinanceCategory.objects.filter(is_active=True)
    
    context = {
        'year': year,
        'budget_lines': budget_lines,
        'categories': categories,
        'years': range(year - 2, year + 2),
    }
    
    return render(request, 'finance/budget_overview.html', context)


@login_required
@role_required('admin', 'finance')
def reports(request):
    """Rapports financiers avec filtres et export PDF."""
    from django.db.models import Sum, Count
    from datetime import date
    
    # Filtres
    year = int(request.GET.get('year', date.today().year))
    month = request.GET.get('month', '')
    site_id = request.GET.get('site', '')
    
    # Transactions de la période
    qs = FinancialTransaction.objects.filter(
        transaction_date__year=year,
        status='valide',
    )
    if month:
        qs = qs.filter(transaction_date__month=int(month))
    if site_id:
        qs = qs.filter(site_id=site_id)
    
    # Calculs
    income_types = ['don', 'dime', 'offrande']
    income = qs.filter(transaction_type__in=income_types).aggregate(
        total=Sum('amount'), count=Count('id')
    )
    expenses = qs.filter(transaction_type='depense').aggregate(
        total=Sum('amount'), count=Count('id')
    )
    
    # Par type
    by_type = qs.values('transaction_type').annotate(
        total=Sum('amount'), count=Count('id')
    ).order_by('-total')
    
    # Par mois (si année complète)
    monthly = []
    if not month:
        for m in range(1, 13):
            m_qs = qs.filter(transaction_date__month=m)
            m_income = m_qs.filter(transaction_type__in=income_types).aggregate(t=Sum('amount'))['t'] or 0
            m_expense = m_qs.filter(transaction_type='depense').aggregate(t=Sum('amount'))['t'] or 0
            monthly.append({
                'month': m,
                'month_name': ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                               'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'][m],
                'income': m_income,
                'expense': m_expense,
                'balance': m_income - m_expense,
            })
    
    # Par méthode de paiement
    by_method = qs.values('payment_method').annotate(
        total=Sum('amount'), count=Count('id')
    ).order_by('-total')
    
    from apps.core.models import Site
    sites = Site.objects.filter(is_active=True)
    
    context = {
        'year': year,
        'month': month,
        'site_id': site_id,
        'sites': sites,
        'years': range(date.today().year, date.today().year - 5, -1),
        'income_total': income['total'] or 0,
        'income_count': income['count'] or 0,
        'expense_total': expenses['total'] or 0,
        'expense_count': expenses['count'] or 0,
        'balance': (income['total'] or 0) - (expenses['total'] or 0),
        'by_type': by_type,
        'monthly': monthly,
        'by_method': by_method,
        'transaction_count': qs.count(),
    }
    
    # Export PDF
    if request.GET.get('export') == 'pdf':
        return _generate_report_pdf(context)
    
    return render(request, 'finance/reports.html', context)


def _generate_report_pdf(context):
    """Génère un PDF du rapport financier."""
    from django.template.loader import render_to_string
    from django.http import HttpResponse
    
    try:
        from weasyprint import HTML, CSS
    except ImportError:
        return HttpResponse("WeasyPrint non installé.", status=500)
    
    html_content = render_to_string('finance/report_pdf.html', context)
    html = HTML(string=html_content)
    pdf = html.write_pdf()
    
    period = f"{context['year']}"
    if context['month']:
        period += f"-{context['month']:0>2}"
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="rapport_financier_{period}.pdf"'
    return response


@login_required
@role_required('admin', 'finance')
def finance_import_excel(request):
    """Import d'un classeur Excel structure pour la finance."""
    if request.method == 'POST':
        form = FinanceExcelImportForm(request.POST, request.FILES)
        if form.is_valid():
            importer = FinanceBundleImporter()
            parser = FinanceExcelWorkbookParser()
            uploaded_file = form.cleaned_data['file']
            dry_run = form.cleaned_data['dry_run']

            try:
                bundle, sections = parser.parse(uploaded_file)
                result = importer.import_bundle(bundle, sections=sections, dry_run=dry_run)
            except FinanceImportError as exc:
                form.add_error(None, str(exc))
            except Exception as exc:
                form.add_error(None, f"Import impossible : {exc}")
            else:
                counts = []
                for model_name in sorted(result['stats']):
                    counters = result['stats'][model_name]
                    counts.append(
                        f"{model_name}: {counters.get('created', 0)} créé(s), {counters.get('updated', 0)} mis à jour"
                    )

                if dry_run:
                    messages.info(
                        request,
                        f"Simulation terminée. Sections lues : {', '.join(sections)}.",
                    )
                else:
                    messages.success(
                        request,
                        f"Import terminé. Sections importées : {', '.join(sections)}.",
                    )

                for line in counts:
                    messages.info(request, line)
                for warning in result['warnings'][:5]:
                    messages.warning(request, warning)
                if len(result['warnings']) > 5:
                    messages.warning(request, 'Des avertissements supplémentaires ont été masqués.')

                return redirect('finance:import_excel')
    else:
        form = FinanceExcelImportForm()

    context = {
        'form': form,
        'sheet_specs': FINANCE_IMPORT_SHEET_SPECS,
    }
    return render(request, 'finance/import_excel.html', context)


@login_required
@role_required('admin', 'finance')
def finance_import_excel_template(request):
    """Télécharge un modèle de classeur pour l'import finance."""
    workbook = build_finance_import_template_workbook()
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"modele_import_finance_{timezone.now().strftime('%Y%m%d')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    workbook.save(response)
    return response


# =============================================================================
# REÇUS FISCAUX
# =============================================================================

from .models import TaxReceipt, OnlineDonation


@login_required
@role_required('admin', 'finance')
def tax_receipt_list(request):
    """Liste des reçus fiscaux."""
    receipts = TaxReceipt.objects.select_related('member', 'issued_by').order_by('-created_at')
    
    # Filtres
    year = request.GET.get('year')
    status = request.GET.get('status')
    
    if year:
        receipts = receipts.filter(fiscal_year=year)
    if status:
        receipts = receipts.filter(status=status)
    
    # Stats
    total_amount = receipts.filter(status='issued').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    paginator = Paginator(receipts, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    
    context = {
        'receipts': page_obj,
        'page_obj': page_obj,
        'total_amount': total_amount,
        'current_year': date.today().year,
        'years': TaxReceipt.objects.values_list('fiscal_year', flat=True).distinct().order_by('-fiscal_year'),
        'statuses': TaxReceipt.Status.choices if hasattr(TaxReceipt, 'Status') else [],
    }
    
    return render(request, 'finance/tax_receipt_list.html', context)


@login_required
@role_required('admin', 'finance')
def tax_receipt_create(request):
    """Créer un reçu fiscal."""
    from apps.members.models import Member
    
    if request.method == 'POST':
        member_id = request.POST.get('member')
        fiscal_year = int(request.POST.get('fiscal_year', date.today().year))
        
        member = get_object_or_404(Member, pk=member_id)
        
        # Calculer le total des dons de l'année
        donations = OnlineDonation.objects.filter(
            donor_email=member.email,
            status='completed',
            created_at__year=fiscal_year
        )
        
        transactions = FinancialTransaction.objects.filter(
            member=member,
            transaction_type__in=['don', 'dime', 'offrande'],
            status='valide',
            transaction_date__year=fiscal_year
        )
        
        # Inclure les dons de campagne (liés par nom du donateur)
        from apps.campaigns.models import Donation as CampaignDonation
        campaign_donations = CampaignDonation.objects.filter(
            donor_name=member.full_name,
            is_cancelled=False,
            donation_date__year=fiscal_year
        )
        
        total = (donations.aggregate(Sum('amount'))['amount__sum'] or 0) + \
                (transactions.aggregate(Sum('amount'))['amount__sum'] or 0) + \
                (campaign_donations.aggregate(Sum('amount'))['amount__sum'] or 0)
        
        if total <= 0:
            messages.error(request, f"Aucun don trouvé pour {member.full_name} en {fiscal_year}")
            return redirect('finance:tax_receipt_create')
        
        # Générer le numéro de reçu
        last_receipt = TaxReceipt.objects.filter(fiscal_year=fiscal_year).order_by('-receipt_number').first()
        if last_receipt:
            try:
                last_num = int(last_receipt.receipt_number.split('-')[-1])
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1
        receipt_number = f"RF-{fiscal_year}-{new_num:04d}"
        
        # Créer le reçu
        receipt = TaxReceipt.objects.create(
            receipt_number=receipt_number,
            member=member,
            fiscal_year=fiscal_year,
            total_amount=total,
            donor_name=member.full_name,
            donor_address=f"{member.address or ''}, {member.postal_code or ''} {member.city or ''}".strip(', '),
            donor_email=member.email or '',
            issued_by=request.user,
            status='draft'
        )
        
        # Rattacher les transactions financières au reçu
        if transactions.exists():
            receipt.transactions.set(transactions)
        
        messages.success(request, f"Reçu fiscal créé pour {member.full_name}")
        return redirect('finance:tax_receipt_detail', pk=receipt.pk)
    
    members = Member.objects.filter(status='actif').order_by('last_name', 'first_name')
    
    context = {
        'members': members,
        'current_year': date.today().year,
        'years': range(date.today().year - 2, date.today().year + 1),
    }
    
    return render(request, 'finance/tax_receipt_create.html', context)


@login_required
@role_required('admin', 'finance')
def tax_receipt_detail(request, pk):
    """Détail d'un reçu fiscal."""
    receipt = get_object_or_404(TaxReceipt.objects.select_related('member', 'issued_by'), pk=pk)
    
    context = {
        'receipt': receipt,
    }
    
    return render(request, 'finance/tax_receipt_detail.html', context)


@login_required
@role_required('admin', 'finance')
def tax_receipt_pdf(request, pk):
    """Générer le PDF d'un reçu fiscal."""
    from .pdf_service import generate_tax_receipt_pdf
    
    receipt = get_object_or_404(TaxReceipt, pk=pk)
    
    # Générer le PDF
    pdf_content = generate_tax_receipt_pdf(receipt)
    
    # Mettre à jour le statut si brouillon
    if receipt.status == 'draft':
        receipt.status = 'issued'
        receipt.issue_date = date.today()
        receipt.save()
    
    from django.http import HttpResponse
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="recu_fiscal_{receipt.receipt_number}.pdf"'
    
    return response


@login_required
@role_required('admin', 'finance')
def tax_receipt_send(request, pk):
    """Envoyer le reçu fiscal par email."""
    from .pdf_service import generate_tax_receipt_pdf
    from django.core.mail import EmailMessage
    
    receipt = get_object_or_404(TaxReceipt, pk=pk)
    
    # Vérifier l'email
    recipient_email = receipt.donor_email or (receipt.member.email if receipt.member else None)
    recipient_name = receipt.donor_name.split()[0] if receipt.donor_name else 'Cher donateur'
    
    if not recipient_email:
        messages.error(request, "Le donateur n'a pas d'adresse email")
        return redirect('finance:tax_receipt_detail', pk=pk)
    
    # Générer le PDF
    pdf_content = generate_tax_receipt_pdf(receipt)
    
    # Envoyer l'email
    email = EmailMessage(
        subject=f"Reçu fiscal {receipt.fiscal_year} - {receipt.receipt_number}",
        body=f"""Bonjour {recipient_name},

Veuillez trouver ci-joint votre reçu fiscal pour l'année {receipt.fiscal_year}.

Montant total des dons : {receipt.total_amount} €

Ce document est à conserver pour votre déclaration d'impôts.

Merci pour votre générosité !

Fraternellement,
L'équipe EEBC""",
        from_email=None,  # Utilise DEFAULT_FROM_EMAIL
        to=[recipient_email],
    )
    email.attach(
        f"recu_fiscal_{receipt.receipt_number}.pdf",
        pdf_content,
        'application/pdf'
    )
    
    try:
        email.send()
        receipt.status = 'sent'
        receipt.sent_date = date.today()
        receipt.save()
        messages.success(request, f"Reçu envoyé à {recipient_email}")
    except Exception as e:
        messages.error(request, f"Erreur d'envoi : {e}")
    
    return redirect('finance:tax_receipt_detail', pk=pk)


@login_required
@role_required('admin', 'finance')
def tax_receipt_bulk_generate(request):
    """Générer les relevés fiscaux en masse pour une année donnée."""
    from apps.members.models import Member
    from apps.campaigns.models import Donation as CampaignDonation

    if request.method == 'POST':
        fiscal_year = int(request.POST.get('fiscal_year', date.today().year))

        members = Member.objects.filter(status='actif').order_by('last_name', 'first_name')
        created_count = 0
        skipped_count = 0

        for member in members:
            # Vérifier qu'il n'y a pas déjà un reçu
            if TaxReceipt.objects.filter(member=member, fiscal_year=fiscal_year).exists():
                skipped_count += 1
                continue

            # 1. Transactions financières
            transactions = FinancialTransaction.objects.filter(
                member=member,
                transaction_date__year=fiscal_year,
                status='valide',
                transaction_type__in=['don', 'dime', 'offrande'],
            )
            total_tx = transactions.aggregate(Sum('amount'))['amount__sum'] or 0

            # 2. Dons en ligne
            from .models import OnlineDonation
            total_online = OnlineDonation.objects.filter(
                member=member, status='completed', created_at__year=fiscal_year,
            ).aggregate(Sum('amount'))['amount__sum'] or 0

            # 3. Dons de campagne
            total_campaign = CampaignDonation.objects.filter(
                donor_name=member.full_name, is_cancelled=False, donation_date__year=fiscal_year,
            ).aggregate(Sum('amount'))['amount__sum'] or 0

            total = total_tx + total_online + total_campaign
            if total <= 0:
                continue

            # Numéro de reçu
            last = TaxReceipt.objects.filter(fiscal_year=fiscal_year).order_by('-receipt_number').first()
            if last:
                try:
                    new_num = int(last.receipt_number.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1
            receipt_number = f"RF-{fiscal_year}-{new_num:04d}"

            receipt = TaxReceipt.objects.create(
                receipt_number=receipt_number,
                member=member,
                fiscal_year=fiscal_year,
                total_amount=total,
                donor_name=member.full_name,
                donor_address=f"{member.address or ''}, {member.postal_code or ''} {member.city or ''}".strip(', '),
                donor_email=member.email or '',
                issued_by=request.user,
                status='draft',
            )
            if transactions.exists():
                receipt.transactions.set(transactions)
            created_count += 1

        if created_count:
            messages.success(request, f"{created_count} relevé(s) fiscal/fiscaux créé(s) pour {fiscal_year}.")
        else:
            messages.info(request, f"Aucun nouveau relevé à créer pour {fiscal_year}.")
        if skipped_count:
            messages.info(request, f"{skipped_count} membre(s) avai(en)t déjà un relevé.")

        return redirect('finance:tax_receipt_list')

    return redirect('finance:tax_receipt_list')


@login_required
@role_required('admin', 'finance')
def tax_receipt_bulk_send(request):
    """Envoyer par email tous les relevés fiscaux émis (issued) qui ont un email."""
    from .pdf_service import generate_tax_receipt_pdf
    from django.core.mail import EmailMessage as DjangoEmail

    if request.method == 'POST':
        fiscal_year = request.POST.get('fiscal_year')
        qs = TaxReceipt.objects.filter(status='issued')
        if fiscal_year:
            qs = qs.filter(fiscal_year=int(fiscal_year))

        # Filtrer ceux qui ont un email
        receipts = [r for r in qs if (r.donor_email or (r.member and r.member.email))]

        sent_count = 0
        error_count = 0

        for receipt in receipts:
            recipient_email = receipt.donor_email or receipt.member.email
            recipient_name = receipt.donor_name.split()[0] if receipt.donor_name else 'Cher donateur'

            try:
                pdf_content = generate_tax_receipt_pdf(receipt)
                email = DjangoEmail(
                    subject=f"Reçu fiscal {receipt.fiscal_year} - {receipt.receipt_number}",
                    body=f"""Bonjour {recipient_name},

Veuillez trouver ci-joint votre reçu fiscal pour l'année {receipt.fiscal_year}.

Montant total des dons : {receipt.total_amount} €

Ce document est à conserver pour votre déclaration d'impôts.

Merci pour votre générosité !

Fraternellement,
L'équipe EEBC""",
                    from_email=None,
                    to=[recipient_email],
                )
                email.attach(
                    f"recu_fiscal_{receipt.receipt_number}.pdf",
                    pdf_content,
                    'application/pdf',
                )
                email.send()
                receipt.status = 'sent'
                receipt.sent_date = date.today()
                receipt.save()
                sent_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f"Failed to send receipt {receipt.receipt_number}: {e}")

        if sent_count:
            messages.success(request, f"{sent_count} reçu(s) envoyé(s) par email.")
        if error_count:
            messages.warning(request, f"{error_count} erreur(s) lors de l'envoi.")
        if not receipts:
            messages.info(request, "Aucun reçu émis avec email à envoyer.")

        return redirect('finance:tax_receipt_list')

    return redirect('finance:tax_receipt_list')


@login_required
@role_required('admin', 'finance')
def batch_retry_ocr(request):
    """
    Relancer l'OCR pour plusieurs justificatifs en échec.
    
    Requirements: 17.4
    """
    if request.method == 'POST':
        receipt_ids = request.POST.getlist('receipt_ids')
        
        if not receipt_ids:
            messages.error(request, "Aucun justificatif sélectionné.")
            return redirect('finance:receipt_proof_list')
        
        try:
            from .tasks import batch_process_ocr
            
            # Filtrer pour ne garder que les justificatifs en échec ou non traités
            failed_receipts = ReceiptProof.objects.filter(
                id__in=receipt_ids,
                ocr_status__in=[ReceiptProof.OCRStatus.ECHEC, ReceiptProof.OCRStatus.NON_TRAITE]
            )
            
            if not failed_receipts.exists():
                messages.warning(request, "Aucun justificatif en échec trouvé dans la sélection.")
                return redirect('finance:receipt_proof_list')
            
            # Réinitialiser le statut des justificatifs sélectionnés
            failed_receipts.update(
                ocr_status=ReceiptProof.OCRStatus.NON_TRAITE,
                ocr_raw_text='',
                ocr_extracted_amount=None,
                ocr_extracted_date=None,
                ocr_confidence=None,
                ocr_processed_at=None
            )
            
            # Lancer le traitement en lot
            receipt_ids_list = list(failed_receipts.values_list('id', flat=True))
            task = batch_process_ocr.delay(receipt_ids_list)
            
            messages.success(
                request, 
                f"Traitement OCR relancé pour {len(receipt_ids_list)} justificatif(s). "
                f"Vous serez notifié par email une fois terminé."
            )
            
        except Exception as e:
            messages.error(request, f"Erreur lors du lancement du traitement en lot : {e}")
    
    return redirect('finance:receipt_proof_list')


# =============================================================================
# API ENDPOINTS POUR AJAX
# =============================================================================

from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)


@login_required
@role_required('admin', 'finance')
def receipt_ocr_status_api(request, pk):
    """
    API endpoint pour vérifier le statut OCR d'un justificatif.
    
    Requirements: 17.2
    """
    try:
        proof = get_object_or_404(ReceiptProof, pk=pk)
        
        return JsonResponse({
            'success': True,
            'status': proof.ocr_status,
            'status_display': proof.get_ocr_status_display(),
            'extracted_amount': str(proof.ocr_extracted_amount) if proof.ocr_extracted_amount else None,
            'extracted_date': proof.ocr_extracted_date.isoformat() if proof.ocr_extracted_date else None,
            'confidence': proof.ocr_confidence,
            'processed_at': proof.ocr_processed_at.isoformat() if proof.ocr_processed_at else None,
            'raw_text_preview': proof.ocr_raw_text[:200] + '...' if len(proof.ocr_raw_text) > 200 else proof.ocr_raw_text,
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@role_required('admin', 'finance')
def batch_ocr_status_api(request):
    """
    API endpoint pour vérifier le statut OCR de plusieurs justificatifs.
    
    Requirements: 17.2
    """
    try:
        receipt_ids = request.GET.get('ids', '').split(',')
        receipt_ids = [int(id.strip()) for id in receipt_ids if id.strip().isdigit()]
        
        if not receipt_ids:
            return JsonResponse({'success': False, 'error': 'No valid IDs provided'})
        
        proofs = ReceiptProof.objects.filter(id__in=receipt_ids)
        
        results = {}
        for proof in proofs:
            results[proof.id] = {
                'status': proof.ocr_status,
                'status_display': proof.get_ocr_status_display(),
                'extracted_amount': str(proof.ocr_extracted_amount) if proof.ocr_extracted_amount else None,
                'confidence': proof.ocr_confidence,
                'processed_at': proof.ocr_processed_at.isoformat() if proof.ocr_processed_at else None,
            }
        
        return JsonResponse({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@role_required('admin', 'finance')
def receipt_proof_list(request):
    """Liste des justificatifs."""
    proofs = ReceiptProof.objects.select_related('transaction', 'uploaded_by').order_by('-uploaded_at')
    
    # Filtres
    ocr_status = request.GET.get('ocr_status')
    if ocr_status:
        proofs = proofs.filter(ocr_status=ocr_status)
    
    context = {
        'proofs': proofs,
        'ocr_statuses': ReceiptProof.OCRStatus.choices if hasattr(ReceiptProof, 'OCRStatus') else [],
    }
    
    return render(request, 'finance/receipt_proof_list.html', context)


@login_required
@role_required('admin', 'finance')
def receipt_proof_upload(request):
    """
    Upload d'un justificatif avec traitement OCR asynchrone.
    
    Requirements: 17.1
    """
    if request.method == 'POST':
        form = ProofUploadForm(request.POST, request.FILES)
        if form.is_valid():
            proof = form.save(commit=False)
            proof.uploaded_by = request.user
            proof.ocr_status = ReceiptProof.OCRStatus.NON_TRAITE
            proof.save()
            
            # Lancer la tâche OCR asynchrone
            from .tasks import process_ocr_task
            
            try:
                task = process_ocr_task.delay(proof.id)
                
                # Stocker l'ID de la tâche pour le suivi (optionnel)
                # On pourrait ajouter un champ task_id au modèle ReceiptProof
                
                messages.success(
                    request, 
                    f"Justificatif uploadé. Le traitement OCR est en cours... "
                    f"Vous serez notifié par email une fois terminé."
                )
                
                # Rediriger vers la liste avec un paramètre pour afficher le statut
                return redirect(f"{request.build_absolute_uri('/finance/receipt-proofs/')}?highlight={proof.id}")
                
            except Exception as e:
                # En cas d'erreur de lancement de la tâche, marquer comme échec
                proof.ocr_status = ReceiptProof.OCRStatus.ECHEC
                proof.save()
                
                messages.error(
                    request, 
                    f"Justificatif uploadé mais le traitement OCR n'a pas pu être lancé: {e}. "
                    f"Vous pouvez le relancer manuellement."
                )
                
                return redirect('finance:receipt_proof_list')
    else:
        form = ProofUploadForm()
    
    context = {
        'form': form,
        'transactions': FinancialTransaction.objects.filter(
            status='en_attente'
        ).order_by('-transaction_date')[:50],
    }
    
    return render(request, 'finance/receipt_proof_upload.html', context)


@login_required
@role_required('admin', 'finance')
def receipt_process_ocr(request, pk):
    """
    Lancer/relancer le traitement OCR sur un justificatif.
    
    Requirements: 17.4
    """
    proof = get_object_or_404(ReceiptProof, pk=pk)
    
    # Vérifier si un traitement est déjà en cours
    if proof.ocr_status == ReceiptProof.OCRStatus.EN_COURS:
        messages.warning(request, "Un traitement OCR est déjà en cours pour ce justificatif.")
        return redirect('finance:receipt_proof_list')
    
    try:
        from .tasks import process_ocr_task
        # Réinitialiser le statut
        proof.ocr_status = ReceiptProof.OCRStatus.NON_TRAITE
        proof.ocr_raw_text = ''
        proof.ocr_extracted_amount = None
        proof.ocr_extracted_date = None
        proof.ocr_confidence = None
        proof.ocr_processed_at = None
        proof.save()
        
        # Lancer la tâche OCR asynchrone
        task = process_ocr_task.delay(proof.id)
        
        messages.success(
            request, 
            f"Traitement OCR relancé pour le justificatif #{proof.id}. "
            f"Vous serez notifié par email une fois terminé."
        )
        
    except Exception as e:
        proof.ocr_status = ReceiptProof.OCRStatus.ECHEC
        proof.save()
        messages.error(request, f"Erreur lors du lancement de l'OCR : {e}")
    
    return redirect('finance:receipt_proof_list')

# =============================================================================
# CRUD POUR LES CATÉGORIES DE BUDGET - OPÉRATIONS MANQUANTES
# =============================================================================

@login_required
@role_required('admin', 'finance')
def budget_category_list(request):
    """Liste des catégories de budget."""
    categories = BudgetCategory.objects.filter(is_active=True).order_by('name')
    
    # Statistiques d'utilisation
    for category in categories:
        category.budgets_count = Budget.objects.filter(items__category=category).distinct().count()
        category.requests_count = BudgetRequest.objects.filter(category=category).count()
        category.total_usage = category.budgets_count + category.requests_count
    
    context = {
        'categories': categories,
        'total_categories': categories.count(),
    }
    
    return render(request, 'finance/budget_category_list.html', context)


@login_required
@role_required('admin', 'finance')
def budget_category_create(request):
    """Créer une nouvelle catégorie de budget."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        color = request.POST.get('color', '#0A36FF')
        
        if not name:
            messages.error(request, 'Le nom de la catégorie est requis.')
        else:
            # Vérifier l'unicité
            if BudgetCategory.objects.filter(name__iexact=name, is_active=True).exists():
                messages.error(request, f'Une catégorie "{name}" existe déjà.')
            else:
                try:
                    category = BudgetCategory.objects.create(
                        name=name,
                        description=description,
                        color=color,
                        is_active=True
                    )
                    
                    messages.success(request, f'Catégorie "{category.name}" créée avec succès.')
                    return redirect('finance:budget_category_list')
                except Exception as e:
                    messages.error(request, f'Erreur lors de la création : {e}')
    
    context = {
        'title': 'Nouvelle catégorie de budget',
        'submit_text': 'Créer la catégorie'
    }
    return render(request, 'finance/budget_category_form.html', context)


@login_required
@role_required('admin', 'finance')
def budget_category_update(request, pk):
    """Modifier une catégorie de budget."""
    category = get_object_or_404(BudgetCategory, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        color = request.POST.get('color', '#0A36FF')
        is_active = 'is_active' in request.POST
        
        if not name:
            messages.error(request, 'Le nom de la catégorie est requis.')
        else:
            # Vérifier l'unicité (exclure la catégorie actuelle)
            if BudgetCategory.objects.filter(name__iexact=name, is_active=True).exclude(pk=pk).exists():
                messages.error(request, f'Une catégorie "{name}" existe déjà.')
            else:
                try:
                    category.name = name
                    category.description = description
                    category.color = color
                    category.is_active = is_active
                    category.save()
                    
                    messages.success(request, f'Catégorie "{category.name}" modifiée avec succès.')
                    return redirect('finance:budget_category_list')
                except Exception as e:
                    messages.error(request, f'Erreur lors de la modification : {e}')
    
    context = {
        'category': category,
        'title': f'Modifier {category.name}',
        'submit_text': 'Enregistrer les modifications'
    }
    return render(request, 'finance/budget_category_form.html', context)


@login_required
@role_required('admin', 'finance')
def budget_category_delete(request, pk):
    """Supprimer une catégorie de budget (soft delete)."""
    category = get_object_or_404(BudgetCategory, pk=pk)
    
    if request.method == 'POST':
        category.is_active = False
        category.save()
        messages.success(request, f'Catégorie "{category.name}" supprimée avec succès.')
        return redirect('finance:budget_category_list')
    
    return render(request, 'finance/budget_category_delete_confirm.html', {'category': category})


# =============================================================================
# CRUD POUR LES CATÉGORIES FINANCIÈRES (TRANSACTIONS)
# =============================================================================

@login_required
@role_required('admin', 'finance')
def finance_category_list(request):
    """Liste des catégories financières."""
    categories = FinanceCategory.objects.filter(is_active=True).order_by('name')
    
    # Statistiques
    for category in categories:
        category.transactions_count = category.transactions.count()
    
    context = {
        'categories': categories,
        'total_categories': categories.count(),
    }
    
    return render(request, 'finance/finance_category_list.html', context)


@login_required
@role_required('admin', 'finance')
def finance_category_create(request):
    """Créer une nouvelle catégorie financière."""
    if request.method == 'POST':
        form = FinanceCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Catégorie "{category.name}" créée avec succès.')
            return redirect('finance:finance_category_list')
    else:
        form = FinanceCategoryForm()
    
    context = {
        'form': form,
        'title': 'Nouvelle catégorie financière',
        'submit_text': 'Créer la catégorie'
    }
    return render(request, 'finance/finance_category_form.html', context)


@login_required
@role_required('admin', 'finance')
def finance_category_update(request, pk):
    """Modifier une catégorie financière."""
    category = get_object_or_404(FinanceCategory, pk=pk)
    
    if request.method == 'POST':
        form = FinanceCategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Catégorie "{category.name}" modifiée avec succès.')
            return redirect('finance:finance_category_list')
    else:
        form = FinanceCategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'title': f'Modifier {category.name}',
        'submit_text': 'Enregistrer les modifications'
    }
    return render(request, 'finance/finance_category_form.html', context)


@login_required
@role_required('admin', 'finance')
def finance_category_delete(request, pk):
    """Supprimer une catégorie financière (soft delete)."""
    category = get_object_or_404(FinanceCategory, pk=pk)
    
    # Vérifier les transactions liées
    transactions_count = category.transactions.count()
    
    if request.method == 'POST':
        if transactions_count > 0:
             # Demander confirmation pour la réassignation
            reassign_to_id = request.POST.get('reassign_to')
            if reassign_to_id:
                try:
                    new_category = FinanceCategory.objects.get(pk=reassign_to_id)
                    category.transactions.update(category=new_category)
                    messages.success(
                        request, 
                        f'{transactions_count} transaction(s) réassignée(s) à "{new_category.name}".'
                    )
                except FinanceCategory.DoesNotExist:
                    messages.error(request, 'Catégorie de réassignation invalide.')
                    return redirect('finance:finance_category_delete', pk=pk)
            else:
                 # Désactiver simplement sans réassigner (les transactions gardent la ref ou on met null?)
                 # FinanceCategory est SET_NULL dans FinancialTransaction.
                 if request.POST.get('action') == 'delete':
                     category.transactions.update(category=None)
                     messages.warning(request, f'{transactions_count} transaction(s) n\'ont plus de catégorie.')
        
        category.is_active = False # Soft delete
        category.save()
        messages.success(request, f'Catégorie "{category.name}" archivée avec succès.')
        return redirect('finance:finance_category_list')
    
    other_categories = FinanceCategory.objects.filter(is_active=True).exclude(pk=pk)
    
    context = {
        'category': category,
        'transactions_count': transactions_count,
        'other_categories': other_categories
    }
    
    return render(request, 'finance/finance_category_confirm_delete.html', context)


@login_required
@role_required('admin', 'finance')
def yearly_comparison(request):
    """
    Graphique comparatif Année N vs Année N-1.
    Recettes et dépenses mensuelles côte à côte.
    """
    from django.db.models.functions import TruncMonth, ExtractMonth

    available_years = list(
        FinancialTransaction.objects.filter(status=FinancialTransaction.Status.VALIDE)
        .dates('transaction_date', 'year', order='DESC')
    )
    available_year_values = [y.year for y in available_years]

    year_param = request.GET.get('year', '').strip()
    if year_param.isdigit() and int(year_param) in available_year_values:
        year_n = int(year_param)
    elif available_year_values:
        year_n = available_year_values[0]
    else:
        year_n = date.today().year
    year_n1 = year_n - 1

    MOIS_LABELS = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin',
                   'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']

    INCOME_TYPES = ['don', 'dime', 'offrande']

    def _monthly_totals(year):
        base_qs = FinancialTransaction.objects.filter(
            status='valide',
            transaction_date__year=year,
        )
        income_qs = base_qs.filter(
            transaction_type__in=INCOME_TYPES,
        ).exclude(
            category__parent__name=DEDICATED_FUNDS_PARENT,
        ).annotate(
            m=ExtractMonth('transaction_date')
        ).values('m').annotate(total=Sum('amount')).order_by('m')

        expense_qs = base_qs.filter(transaction_type='depense').annotate(
            m=ExtractMonth('transaction_date')
        ).values('m').annotate(total=Sum('amount')).order_by('m')

        income_map = {r['m']: float(r['total']) for r in income_qs}
        expense_map = {r['m']: float(r['total']) for r in expense_qs}

        income = [income_map.get(i, 0) for i in range(1, 13)]
        expense = [expense_map.get(i, 0) for i in range(1, 13)]
        return income, expense

    income_n, expense_n = _monthly_totals(year_n)
    income_n1, expense_n1 = _monthly_totals(year_n1)

    context = {
        'year_n': year_n,
        'year_n1': year_n1,
        'months': MOIS_LABELS,
        'income_n': income_n,
        'expense_n': expense_n,
        'income_n1': income_n1,
        'expense_n1': expense_n1,
        'total_income_n': sum(income_n),
        'total_expense_n': sum(expense_n),
        'total_income_n1': sum(income_n1),
        'total_expense_n1': sum(expense_n1),
        'net_total_n': sum(income_n) - sum(expense_n),
        'net_total_n1': sum(income_n1) - sum(expense_n1),
        'available_years': available_year_values,
        'selected_year': year_n,
    }
    return render(request, 'finance/yearly_comparison.html', context)


# =============================================================================
# DONS EN LIGNE
# =============================================================================

@login_required
@role_required('admin', 'finance')
def online_donation_list(request):
    """Liste des dons en ligne (Stripe)."""
    from .models import OnlineDonation
    
    qs = OnlineDonation.objects.select_related('transaction', 'site', 'member').order_by('-created_at')
    
    # Filtres
    status = request.GET.get('status', '')
    donation_type = request.GET.get('type', '')
    date_from = request.GET.get('from', '')
    date_to = request.GET.get('to', '')
    
    if status:
        qs = qs.filter(status=status)
    if donation_type:
        qs = qs.filter(donation_type=donation_type)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    
    # Stats
    stats = qs.filter(status='completed').aggregate(
        total=Sum('amount'),
        count=Count('id'),
    )
    
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    
    context = {
        'donations': page,
        'stats': stats,
        'filter_status': status,
        'filter_type': donation_type,
        'filter_from': date_from,
        'filter_to': date_to,
    }
    return render(request, 'finance/online_donations.html', context)


# =============================================================================
# RÉCAPITULATIF ANNUEL PAR MEMBRE
# =============================================================================

@login_required
@role_required('admin', 'finance')
def member_annual_summary(request):
    """Récapitulatif annuel des dons par membre."""
    from apps.members.models import Member
    
    year = int(request.GET.get('year', date.today().year))
    site_id = request.GET.get('site', '')
    
    income_types = ['don', 'dime', 'offrande']
    
    # Membres ayant des transactions cette année
    members_qs = Member.objects.filter(
        transactions__transaction_date__year=year,
        transactions__status='valide',
        transactions__transaction_type__in=income_types,
        transactions__is_deleted=False,
    ).distinct()
    
    if site_id:
        members_qs = members_qs.filter(site_id=site_id)
    
    # Annoter avec les totaux
    members_qs = members_qs.annotate(
        total_dons=Sum('transactions__amount', filter=Q(
            transactions__transaction_type='don',
            transactions__transaction_date__year=year,
            transactions__status='valide',
            transactions__is_deleted=False,
        )),
        total_dimes=Sum('transactions__amount', filter=Q(
            transactions__transaction_type='dime',
            transactions__transaction_date__year=year,
            transactions__status='valide',
            transactions__is_deleted=False,
        )),
        total_offrandes=Sum('transactions__amount', filter=Q(
            transactions__transaction_type='offrande',
            transactions__transaction_date__year=year,
            transactions__status='valide',
            transactions__is_deleted=False,
        )),
    ).order_by('last_name', 'first_name')
    
    # Calculer les totaux globaux
    grand_total = {'dons': Decimal('0'), 'dimes': Decimal('0'), 'offrandes': Decimal('0')}
    members_data = []
    for m in members_qs:
        dons = m.total_dons or Decimal('0')
        dimes = m.total_dimes or Decimal('0')
        offrandes = m.total_offrandes or Decimal('0')
        total = dons + dimes + offrandes
        members_data.append({
            'member': m,
            'dons': dons,
            'dimes': dimes,
            'offrandes': offrandes,
            'total': total,
        })
        grand_total['dons'] += dons
        grand_total['dimes'] += dimes
        grand_total['offrandes'] += offrandes
    
    grand_total['total'] = grand_total['dons'] + grand_total['dimes'] + grand_total['offrandes']
    
    from apps.core.models import Site
    sites = Site.objects.filter(is_active=True)
    
    context = {
        'year': year,
        'site_id': site_id,
        'sites': sites,
        'years': range(date.today().year, date.today().year - 5, -1),
        'members_data': members_data,
        'grand_total': grand_total,
        'member_count': len(members_data),
    }
    return render(request, 'finance/member_summary.html', context)


@login_required
@role_required('admin', 'finance')
def member_donation_detail(request, member_id):
    """Détail des dons d'un membre pour une année."""
    from apps.members.models import Member
    
    member = get_object_or_404(Member, pk=member_id)
    year = int(request.GET.get('year', date.today().year))
    
    income_types = ['don', 'dime', 'offrande']
    transactions = FinancialTransaction.objects.filter(
        member=member,
        transaction_date__year=year,
        status='valide',
        transaction_type__in=income_types,
    ).order_by('transaction_date')
    
    # Totaux par type
    totals = transactions.values('transaction_type').annotate(
        total=Sum('amount'), count=Count('id')
    )
    totals_dict = {t['transaction_type']: t for t in totals}
    
    # Par mois
    monthly = []
    for m in range(1, 13):
        m_txs = transactions.filter(transaction_date__month=m)
        m_total = m_txs.aggregate(t=Sum('amount'))['t'] or 0
        monthly.append({
            'month': m,
            'month_name': ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                           'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'][m],
            'total': m_total,
            'count': m_txs.count(),
        })
    
    # Dons en ligne
    from .models import OnlineDonation
    online = OnlineDonation.objects.filter(
        member=member, status='completed', created_at__year=year
    ).order_by('created_at')
    online_total = online.aggregate(t=Sum('amount'))['t'] or 0
    
    context = {
        'member': member,
        'year': year,
        'years': range(date.today().year, date.today().year - 5, -1),
        'transactions': transactions,
        'totals': totals_dict,
        'monthly': monthly,
        'online_donations': online,
        'online_total': online_total,
        'grand_total': (transactions.aggregate(t=Sum('amount'))['t'] or 0) + online_total,
    }
    return render(request, 'finance/member_donation_detail.html', context)


@login_required
@role_required('admin', 'finance')
def member_donation_detail_pdf(request, member_id):
    """Export PDF du récapitulatif d'un membre."""
    from apps.members.models import Member
    from django.template.loader import render_to_string
    
    member = get_object_or_404(Member, pk=member_id)
    year = int(request.GET.get('year', date.today().year))
    
    income_types = ['don', 'dime', 'offrande']
    transactions = FinancialTransaction.objects.filter(
        member=member, transaction_date__year=year,
        status='valide', transaction_type__in=income_types,
    ).order_by('transaction_date')
    
    totals = transactions.values('transaction_type').annotate(total=Sum('amount'))
    totals_dict = {t['transaction_type']: t['total'] for t in totals}
    grand_total = sum(totals_dict.values(), Decimal('0'))
    
    try:
        from weasyprint import HTML
    except ImportError:
        return HttpResponse("WeasyPrint non installé.", status=500)
    
    html_content = render_to_string('finance/member_donation_detail_pdf.html', {
        'member': member,
        'year': year,
        'transactions': transactions,
        'totals': totals_dict,
        'grand_total': grand_total,
    })
    
    pdf = HTML(string=html_content).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="recapitulatif_{member.member_id}_{year}.pdf"'
    return response
