"""Vues pour le module Finance."""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from .models import FinancialTransaction, FinanceCategory, ReceiptProof, BudgetLine
from .forms import TransactionForm, ProofUploadForm


@login_required
def dashboard(request):
    """Tableau de bord financier."""
    today = date.today()
    start_of_month = today.replace(day=1)
    start_of_year = today.replace(month=1, day=1)
    
    # Stats du mois
    month_transactions = FinancialTransaction.objects.filter(
        transaction_date__gte=start_of_month,
        status=FinancialTransaction.Status.VALIDE
    )
    
    month_income = month_transactions.filter(
        transaction_type__in=['don', 'dime', 'offrande']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    month_expenses = month_transactions.filter(
        transaction_type='depense'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Stats de l'année
    year_transactions = FinancialTransaction.objects.filter(
        transaction_date__gte=start_of_year,
        status=FinancialTransaction.Status.VALIDE
    )
    
    year_income = year_transactions.filter(
        transaction_type__in=['don', 'dime', 'offrande']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    year_expenses = year_transactions.filter(
        transaction_type='depense'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Transactions récentes
    recent_transactions = FinancialTransaction.objects.select_related(
        'category', 'member'
    ).order_by('-transaction_date', '-created_at')[:10]
    
    # Transactions en attente
    pending_count = FinancialTransaction.objects.filter(
        status=FinancialTransaction.Status.EN_ATTENTE
    ).count()
    
    context = {
        'month_income': month_income,
        'month_expenses': month_expenses,
        'month_balance': month_income - month_expenses,
        'year_income': year_income,
        'year_expenses': year_expenses,
        'year_balance': year_income - year_expenses,
        'recent_transactions': recent_transactions,
        'pending_count': pending_count,
    }
    
    return render(request, 'finance/dashboard.html', context)


@login_required
def transaction_list(request):
    """Liste des transactions avec filtres."""
    transactions = FinancialTransaction.objects.select_related(
        'category', 'member', 'recorded_by'
    ).order_by('-transaction_date')
    
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
    
    context = {
        'transactions': transactions,
        'transaction_types': FinancialTransaction.TransactionType.choices,
        'statuses': FinancialTransaction.Status.choices,
    }
    
    return render(request, 'finance/transaction_list.html', context)


@login_required
def transaction_create(request):
    """Créer une nouvelle transaction."""
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.recorded_by = request.user
            transaction.save()
            messages.success(request, f"Transaction {transaction.reference} créée.")
            return redirect('finance:transaction_detail', pk=transaction.pk)
    else:
        form = TransactionForm()
    
    return render(request, 'finance/transaction_form.html', {'form': form})


@login_required
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
@permission_required('finance.change_financialtransaction')
def transaction_validate(request, pk):
    """Valider une transaction."""
    transaction = get_object_or_404(FinancialTransaction, pk=pk)
    
    if transaction.status == FinancialTransaction.Status.EN_ATTENTE:
        transaction.status = FinancialTransaction.Status.VALIDE
        transaction.validated_by = request.user
        transaction.validated_at = timezone.now()
        transaction.save()
        messages.success(request, f"Transaction {transaction.reference} validée.")
    
    return redirect('finance:transaction_detail', pk=pk)


@login_required
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
def reports(request):
    """Rapports financiers."""
    # Placeholder pour les rapports avancés
    return render(request, 'finance/reports.html')
