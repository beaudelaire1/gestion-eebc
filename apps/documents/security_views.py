"""Secure wrappers for the document library."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, render

from . import views as legacy_views
from .forms import DocumentUploadForm
from .models import Document, DocumentShare
from .security import is_active_browser_document, validate_document_upload


def document_upload(request):
    if request.method == 'POST':
        files = request.FILES.getlist('file')
        for uploaded_file in files:
            try:
                validate_document_upload(uploaded_file)
            except ValidationError as exc:
                messages.error(request, f"{uploaded_file.name} : {' '.join(exc.messages)}")
                form = DocumentUploadForm(request.POST, request.FILES)
                return render(
                    request,
                    'documents/document_upload.html',
                    {'form': form},
                    status=400,
                )
    return legacy_views.document_upload(request)


def document_stream(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    if is_active_browser_document(doc.file_name, doc.file_type):
        # Historical active files are never rendered in the application origin.
        return legacy_views.document_download(request, pk)
    return legacy_views.document_stream(request, pk)


def document_preview(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    if is_active_browser_document(doc.file_name, doc.file_type):
        return HttpResponse('Aperçu interdit pour ce type de fichier.', status=415)
    return legacy_views.document_preview(request, pk)


def shared_access(request, token):
    share = get_object_or_404(DocumentShare, share_token=token)
    doc = share.document
    if request.GET.get('stream') == '1' and is_active_browser_document(doc.file_name, doc.file_type):
        if share.is_expired:
            return legacy_views.shared_access(request, token)
        response = FileResponse(
            doc.file.open('rb'),
            content_type='application/octet-stream',
        )
        response['Content-Disposition'] = f'attachment; filename="{doc.file_name}"'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
    return legacy_views.shared_access(request, token)
