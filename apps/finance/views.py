"""Vues pour le module Finance."""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import JsonResponse
from datetime import date, timedelta
from decimal import Decimal

from .models import FinancialTransaction, FinanceCategory, ReceiptProof, BudgetLine
from .forms import TransactionForm, ProofUploadForm
from .services import TransactionService, BudgetService
from apps.core.permissions import role_required


@login_required
@role_required('admin', 'finance')
def dashboard(request):
    """
    Tableau de bord financier.
    
    Utilise TransactionService pour récupérer les statistiques.
    Requirements: 7.2, 21.1
    """
    # Déléguer la logique métier au service
    stats = TransactionService.get_dashboard_stats()
    
    # Données pour le graphique d'évolution des dons (12 mois)
    donations_chart_data = TransactionService.get_monthly_donations_data(12)
    
    # Données pour le graphique de répartition des dépenses (12 mois)
    expenses_chart_data = TransactionService.get_expenses_distribution_data(12)
    
    context = {
        'month_income': stats['month_income'],
        'month_expenses': stats['month_expenses'],
        'month_balance': stats['month_balance'],
        'year_income': stats['year_income'],
        'year_expenses': stats['year_expenses'],
        'year_balance': stats['year_balance'],
        'recent_transactions': stats['recent_transactions'],
        'pending_count': stats['pending_count'],
        'donations_chart_data': donations_chart_data,
        'expenses_chart_data': expenses_chart_data,
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
    
    # Limiter le nombre de mois pour éviter les abus
    if months not in [3, 6, 12, 24]:
        months = 12
    
    # Récupérer les données via le service selon le type
    if chart_type == 'expenses':
        chart_data = TransactionService.get_expenses_distribution_data(months)
    else:  # donations par défaut
        chart_data = TransactionService.get_monthly_donations_data(months)
    
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
    
    context = {
        'transactions': transactions,
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
        form = TransactionForm()
    
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
    """Rapports financiers."""
    # Placeholder pour les rapports avancés
    return render(request, 'finance/reports.html')


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
    
    context = {
        'receipts': receipts,
        'total_amount': total_amount,
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
@role_required('admin', 'finance')
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
