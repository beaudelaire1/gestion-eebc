"""Authorization and input boundary for imports/exports."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.core.permissions import role_required
from apps.core.upload_security import validate_spreadsheet_upload
from . import views as legacy_views
from .forms import ImportForm
from .models import ImportLog


@login_required
@role_required('admin', 'secretariat')
def import_create(request):
    if request.method == 'POST':
        uploaded = request.FILES.get('file_path') or request.FILES.get('file')
        if uploaded:
            try:
                validate_spreadsheet_upload(
                    uploaded,
                    allowed_extensions=('.xlsx', '.xls'),
                    max_bytes=10 * 1024 * 1024,
                )
            except ValidationError as exc:
                form = ImportForm(request.POST, request.FILES)
                messages.error(request, ' '.join(exc.messages))
                return render(request, 'imports/import_create.html', {
                    'form': form,
                    'import_types': ImportLog.ImportType.choices,
                }, status=400)
    return legacy_views.import_create(request)


@login_required
@role_required('admin', 'secretariat')
def import_delete(request, pk):
    return legacy_views.import_delete(request, pk)


@login_required
@role_required('admin', 'secretariat')
@require_POST
def import_bulk_delete(request):
    return legacy_views.import_bulk_delete(request)


@login_required
@role_required('admin', 'secretariat')
def export_members(request):
    return legacy_views.export_members(request)


@login_required
@role_required('admin', 'secretariat')
def export_children(request):
    return legacy_views.export_children(request)


@login_required
@role_required('admin', 'secretariat')
def export_young_members(request):
    return legacy_views.export_young_members(request)


@login_required
@role_required('admin', 'secretariat')
def export_groups(request):
    return legacy_views.export_groups(request)


@login_required
@role_required('admin')
def export_inventory(request):
    return legacy_views.export_inventory(request)


@login_required
@role_required('admin')
def export_transport(request):
    return legacy_views.export_transport(request)


@login_required
@role_required('admin', 'secretariat')
def export_communication(request):
    return legacy_views.export_communication(request)
