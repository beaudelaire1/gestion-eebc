"""HTTP method boundary for state-changing finance actions."""
from django.views.decorators.http import require_POST

from . import views
from . import budget_views


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
