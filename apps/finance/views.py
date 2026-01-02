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


# =============================================================================
# REÇUS FISCAUX
# =============================================================================

from .models import TaxReceipt, OnlineDonation


@login_required
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
    
    context = {
        'receipts': receipts,
        'total_amount': total_amount,
        'years': TaxReceipt.objects.values_list('fiscal_year', flat=True).distinct().order_by('-fiscal_year'),
        'statuses': TaxReceipt.Status.choices if hasattr(TaxReceipt, 'Status') else [],
    }
    
    return render(request, 'finance/tax_receipt_list.html', context)


@login_required
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
        
        total = (donations.aggregate(Sum('amount'))['amount__sum'] or 0) + \
                (transactions.aggregate(Sum('amount'))['amount__sum'] or 0)
        
        if total <= 0:
            messages.error(request, f"Aucun don trouvé pour {member.full_name} en {fiscal_year}")
            return redirect('finance:tax_receipt_create')
        
        # Générer le numéro de reçu
        last_receipt = TaxReceipt.objects.filter(fiscal_year=fiscal_year).order_by('-receipt_number').first()
        if last_receipt:
            try:
                last_num = int(last_receipt.receipt_number.split('-')[-1])
                new_num = last_num + 1
            except:
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
def tax_receipt_detail(request, pk):
    """Détail d'un reçu fiscal."""
    receipt = get_object_or_404(TaxReceipt.objects.select_related('member', 'issued_by'), pk=pk)
    
    context = {
        'receipt': receipt,
    }
    
    return render(request, 'finance/tax_receipt_detail.html', context)


@login_required
def tax_receipt_pdf(request, pk):
    """Générer le PDF d'un reçu fiscal."""
    from .pdf_service import TaxReceiptPDFService
    
    receipt = get_object_or_404(TaxReceipt, pk=pk)
    
    # Générer le PDF
    pdf_service = TaxReceiptPDFService()
    pdf_content = pdf_service.generate_receipt_pdf(receipt)
    
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
def tax_receipt_send(request, pk):
    """Envoyer le reçu fiscal par email."""
    from .pdf_service import TaxReceiptPDFService
    from django.core.mail import EmailMessage
    
    receipt = get_object_or_404(TaxReceipt, pk=pk)
    
    # Vérifier l'email
    recipient_email = receipt.donor_email or (receipt.member.email if receipt.member else None)
    recipient_name = receipt.donor_name.split()[0] if receipt.donor_name else 'Cher donateur'
    
    if not recipient_email:
        messages.error(request, "Le donateur n'a pas d'adresse email")
        return redirect('finance:tax_receipt_detail', pk=pk)
    
    # Générer le PDF
    pdf_service = TaxReceiptPDFService()
    pdf_content = pdf_service.generate_receipt_pdf(receipt)
    
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


# =============================================================================
# JUSTIFICATIFS AVEC OCR
# =============================================================================

@login_required
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
def receipt_proof_upload(request):
    """Upload d'un justificatif."""
    if request.method == 'POST':
        form = ProofUploadForm(request.POST, request.FILES)
        if form.is_valid():
            proof = form.save(commit=False)
            proof.uploaded_by = request.user
            proof.save()
            messages.success(request, "Justificatif uploadé. Vous pouvez lancer l'OCR.")
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
def receipt_process_ocr(request, pk):
    """Lancer le traitement OCR sur un justificatif."""
    from .ocr_service import OCRService
    
    proof = get_object_or_404(ReceiptProof, pk=pk)
    
    try:
        ocr_service = OCRService()
        result = ocr_service.process_receipt(proof.image.path)
        
        proof.ocr_status = 'termine'
        proof.ocr_raw_text = result.get('raw_text', '')
        proof.ocr_extracted_amount = result.get('amount')
        proof.ocr_extracted_date = result.get('date')
        proof.ocr_confidence = result.get('confidence', 0)
        proof.save()
        
        messages.success(request, f"OCR terminé. Montant détecté : {proof.ocr_extracted_amount or 'N/A'}")
    except Exception as e:
        proof.ocr_status = 'echec'
        proof.save()
        messages.error(request, f"Erreur OCR : {e}")
    
    return redirect('finance:receipt_proof_list')
