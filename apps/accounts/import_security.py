"""Secure bulk account import entry point."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden
from django.shortcuts import render

from apps.core.security import user_has_any_role
from apps.core.upload_security import validate_spreadsheet_upload
from . import views as legacy_views
from .forms import UserBulkImportForm


@login_required
def secure_user_bulk_import_view(request):
    if not user_has_any_role(request.user, 'admin'):
        return HttpResponseForbidden("L'import de comptes est réservé aux administrateurs.")

    if request.method == 'POST':
        uploaded = request.FILES.get('file')
        if uploaded:
            try:
                validate_spreadsheet_upload(
                    uploaded,
                    allowed_extensions=('.xlsx', '.xls', '.csv'),
                    max_bytes=5 * 1024 * 1024,
                )
            except ValidationError as exc:
                form = UserBulkImportForm(request.POST, request.FILES)
                form.add_error('file', exc)
                return render(request, 'accounts/user_bulk_import.html', {'form': form}, status=400)

    return legacy_views.user_bulk_import_view(request)
