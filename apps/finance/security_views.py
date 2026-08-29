"""Security boundary for finance input and state-changing actions."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.core.permissions import role_required
from apps.core.upload_security import validate_spreadsheet_upload
from . import views
from . import budget_views
from .forms import FinanceExcelImportForm
from .import_services import FINANCE_IMPORT_SHEET_SPECS
from .models import TaxReceipt


@login_required
@role_required('admin', 'finance')
def finance_import_excel(request):
    if request.method == 'POST':
        uploaded = request.FILES.get('file')
        if uploaded:
            try:
                validate_spreadsheet_upload(
                    uploaded,
                    allowed_extensions=('.xlsx',),
                    max_bytes=10 * 1024 * 1024,
                )
            except ValidationError as exc:
                form = FinanceExcelImportForm(request.POST, request.FILES)
                form.add_error('file', exc)
                return render(request, 'finance/import_excel.html', {
                    'form': form,
                    'sheet_specs': FINANCE_IMPORT_SHEET_SPECS,
                }, status=400)
    return views.finance_import_excel(request)


@login_required
@role_required('admin', 'finance')
def tax_receipt_pdf(request, pk):
    """Render a receipt without mutating its business status on GET."""
    from .pdf_service import generate_tax_receipt_pdf

    receipt = get_object_or_404(TaxReceipt, pk=pk)
    pdf_content = generate_tax_receipt_pdf(receipt)
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="recu_fiscal_{receipt.receipt_number}.pdf"'
    response['Cache-Control'] = 'private, no-store'
    return response


@require_POST
def transaction_validate(request, pk):
    return views.transaction_validate(request, pk)


@require_POST
def proof_upload(request, pk):
    return views.proof_upload(request, pk)


@require_POST
def tax_receipt_send(request, pk):
    return views.tax_receipt_send(request, pk)


@require_POST
def tax_receipt_bulk_generate(request):
    return views.tax_receipt_bulk_generate(request)


@require_POST
def tax_receipt_bulk_send(request):
    return views.tax_receipt_bulk_send(request)


@require_POST
def budget_approve_detailed(request, budget_id):
    return budget_views.budget_approve_detailed(request, budget_id)


@require_POST
def budget_submit(request, budget_id):
    return budget_views.budget_submit(request, budget_id)


@require_POST
def receipt_process_ocr(request, pk):
    return views.receipt_process_ocr(request, pk)


@require_POST
def batch_retry_ocr(request):
    return views.batch_retry_ocr(request)
