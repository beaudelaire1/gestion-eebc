import mimetypes
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.utils import timezone

from apps.core.permissions import role_required
from .models import Document, DocumentCategory, DocumentShare
from .forms import DocumentUploadForm, DocumentEditForm, DocumentShareForm, CategoryForm
from .services import validate_file, detect_media_type, get_mime_type, get_documents_stats, log_access, share_document_by_email, create_default_categories, generate_preview_html


@login_required
def document_list(request):
    qs = Document.objects.select_related('category', 'uploaded_by')

    # Masquer les confidentiels pour les non-admin
    user = request.user
    if not (user.is_superuser or getattr(user, 'is_admin', False) or user.has_any_role('admin', 'secretariat')):
        qs = qs.filter(is_confidential=False)

    # Filtres
    category_slug = request.GET.get('category')
    media_type = request.GET.get('media_type')
    source = request.GET.get('source')
    search = request.GET.get('q')
    confidential = request.GET.get('confidential')

    if category_slug:
        qs = qs.filter(category__slug=category_slug)
    if media_type:
        qs = qs.filter(media_type=media_type)
    if source:
        qs = qs.filter(source=source)
    if confidential == '1':
        qs = qs.filter(is_confidential=True)
    if search:
        qs = qs.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(file_name__icontains=search) |
            Q(tags__icontains=search)
        )

    paginator = Paginator(qs, 24)
    page_obj = paginator.get_page(request.GET.get('page'))

    categories = DocumentCategory.objects.all()
    stats = get_documents_stats(user)

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'media_types': Document.MediaType.choices,
        'sources': Document.Source.choices,
        'current_category': category_slug,
        'current_media_type': media_type,
        'current_source': source,
        'search': search or '',
        'stats': stats,
    }
    return render(request, 'documents/document_list.html', context)


@login_required
@role_required('admin', 'secretariat', 'finance')
def document_upload(request):
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        files = request.FILES.getlist('file')

        if not files:
            messages.error(request, "Veuillez sélectionner au moins un fichier.")
            return render(request, 'documents/document_upload.html', {'form': form})

        success_count = 0
        for uploaded_file in files:
            media_type, error = validate_file(uploaded_file)
            if error:
                messages.error(request, f"{uploaded_file.name} : {error}")
                continue

            # Pour les uploads multiples, générer le titre à partir du nom
            title = form.cleaned_data.get('title') if len(files) == 1 and form.is_valid() else ''
            if not title:
                title = uploaded_file.name.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()

            doc = Document(
                title=title,
                description=form.cleaned_data.get('description', '') if form.is_valid() else '',
                file=uploaded_file,
                file_name=uploaded_file.name,
                file_size=uploaded_file.size,
                file_type=uploaded_file.content_type or get_mime_type(uploaded_file.name),
                media_type=media_type,
                category=form.cleaned_data.get('category') if form.is_valid() else None,
                source=form.cleaned_data.get('source', 'manual') if form.is_valid() else 'manual',
                tags=form.cleaned_data.get('tags', '') if form.is_valid() else '',
                is_confidential=form.cleaned_data.get('is_confidential', False) if form.is_valid() else False,
                uploaded_by=request.user,
            )
            doc.save()
            success_count += 1

        if success_count:
            messages.success(request, f"{success_count} document(s) importé(s) avec succès.")
            return redirect('documents:list')

        return render(request, 'documents/document_upload.html', {'form': form})
    else:
        form = DocumentUploadForm()

    return render(request, 'documents/document_upload.html', {'form': form})


@login_required
def document_detail(request, pk):
    doc = get_object_or_404(Document.objects.select_related('category', 'uploaded_by', 'linked_member'), pk=pk)

    user = request.user
    if doc.is_confidential and not (user.is_superuser or getattr(user, 'is_admin', False) or user.has_any_role('admin', 'secretariat')):
        raise Http404

    log_access(doc, user, 'view', request)

    access_logs = doc.access_logs.select_related('user').order_by('-accessed_at')[:20]
    shares = doc.shares.select_related('shared_by').order_by('-shared_at')[:10]

    context = {
        'document': doc,
        'access_logs': access_logs,
        'shares': shares,
    }
    return render(request, 'documents/document_detail.html', context)


@login_required
def document_download(request, pk):
    doc = get_object_or_404(Document, pk=pk)

    user = request.user
    if doc.is_confidential and not (user.is_superuser or getattr(user, 'is_admin', False) or user.has_any_role('admin', 'secretariat')):
        raise Http404

    log_access(doc, user, 'download', request)

    response = FileResponse(doc.file.open('rb'), content_type=doc.file_type or 'application/octet-stream')

    # Support Range headers pour streaming audio/vidéo
    if doc.media_type in ('audio', 'video'):
        response['Accept-Ranges'] = 'bytes'

    response['Content-Disposition'] = f'attachment; filename="{doc.file_name}"'
    return response


@login_required
def document_stream(request, pk):
    """Sert le fichier en inline (pour lecteur audio/vidéo et aperçu PDF)."""
    doc = get_object_or_404(Document, pk=pk)

    user = request.user
    if doc.is_confidential and not (user.is_superuser or getattr(user, 'is_admin', False) or user.has_any_role('admin', 'secretariat')):
        raise Http404

    content_type = doc.file_type or get_mime_type(doc.file_name)
    response = FileResponse(doc.file.open('rb'), content_type=content_type)
    response['Content-Disposition'] = f'inline; filename="{doc.file_name}"'

    if doc.media_type in ('audio', 'video'):
        response['Accept-Ranges'] = 'bytes'

    return response


@login_required
def document_preview(request, pk):
    """Génère un aperçu HTML pour les fichiers texte, Word, Excel, PowerPoint."""
    doc = get_object_or_404(Document, pk=pk)

    user = request.user
    if doc.is_confidential and not (user.is_superuser or getattr(user, 'is_admin', False) or user.has_any_role('admin', 'secretariat')):
        raise Http404

    html_content, error = generate_preview_html(doc)

    return render(request, 'documents/document_preview_frame.html', {
        'document': doc,
        'preview_html': html_content,
        'preview_error': error,
    })


@login_required
@role_required('admin', 'secretariat', 'finance')
def document_edit(request, pk):
    doc = get_object_or_404(Document, pk=pk)

    if request.method == 'POST':
        form = DocumentEditForm(request.POST, instance=doc)
        if form.is_valid():
            form.save()
            messages.success(request, f"Document « {doc.title} » mis à jour.")
            return redirect('documents:detail', pk=doc.pk)
    else:
        form = DocumentEditForm(instance=doc)

    return render(request, 'documents/document_edit.html', {'form': form, 'document': doc})


@login_required
@role_required('admin')
def document_delete(request, pk):
    doc = get_object_or_404(Document, pk=pk)

    if request.method == 'POST':
        title = doc.title
        doc.file.delete(save=False)
        doc.delete()
        messages.success(request, f"Document « {title} » supprimé.")
        return redirect('documents:list')

    return render(request, 'documents/document_confirm_delete.html', {'document': doc})


@login_required
@role_required('admin', 'secretariat', 'finance')
def document_share(request, pk):
    doc = get_object_or_404(Document, pk=pk)

    if doc.is_confidential:
        messages.error(request, "Les documents confidentiels ne peuvent pas être partagés.")
        return redirect('documents:detail', pk=doc.pk)

    if request.method == 'POST':
        form = DocumentShareForm(request.POST)
        if form.is_valid():
            share = share_document_by_email(
                document=doc,
                user=request.user,
                recipient_email=form.cleaned_data['recipient_email'],
                recipient_name=form.cleaned_data.get('recipient_name', ''),
                message=form.cleaned_data.get('message', ''),
                request=request,
            )
            if getattr(share, '_email_sent', False):
                messages.success(request, f"Document partagé avec {share.recipient_email}. Lien valide 7 jours.")
            else:
                messages.warning(request, f"Lien de partage créé mais l'email n'a pas pu être envoyé à {share.recipient_email}. Erreur : {getattr(share, '_email_error', 'inconnue')}")
            return redirect('documents:detail', pk=doc.pk)
    else:
        form = DocumentShareForm()

    return render(request, 'documents/document_share.html', {'form': form, 'document': doc})


def shared_access(request, token):
    """Accès public via lien de partage (pas de login requis)."""
    share = get_object_or_404(DocumentShare, share_token=token)

    if share.is_expired:
        return render(request, 'documents/document_shared_expired.html', {'share': share})

    # Marquer comme consulté
    if not share.accessed_at:
        share.accessed_at = timezone.now()
        share.save(update_fields=['accessed_at'])

    doc = share.document

    # Téléchargement direct si demandé
    if request.GET.get('download') == '1':
        response = FileResponse(doc.file.open('rb'), content_type=doc.file_type or 'application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{doc.file_name}"'
        return response

    # Streaming inline
    if request.GET.get('stream') == '1':
        content_type = doc.file_type or get_mime_type(doc.file_name)
        response = FileResponse(doc.file.open('rb'), content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{doc.file_name}"'
        if doc.media_type in ('audio', 'video'):
            response['Accept-Ranges'] = 'bytes'
        return response

    return render(request, 'documents/document_shared_access.html', {'share': share, 'document': doc})


@login_required
@role_required('admin', 'secretariat')
def category_list(request):
    categories = DocumentCategory.objects.annotate(doc_count=Q(documents__isnull=False)).prefetch_related('documents')

    # Créer les catégories par défaut si aucune n'existe
    if not categories.exists():
        create_default_categories()
        categories = DocumentCategory.objects.all()

    # Formulaire d'ajout
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Catégorie créée.")
            return redirect('documents:categories')
    else:
        form = CategoryForm()

    # Compter les documents par catégorie
    cat_list = []
    for cat in DocumentCategory.objects.all().order_by('order', 'name'):
        cat.doc_count = cat.documents.count()
        cat_list.append(cat)

    return render(request, 'documents/category_list.html', {
        'categories': cat_list,
        'form': form,
    })


@login_required
@role_required('admin', 'secretariat')
def document_stats(request):
    stats = get_documents_stats(request.user)
    categories = DocumentCategory.objects.all()

    cat_stats = []
    for cat in categories:
        docs = cat.documents.all()
        from django.db.models import Sum
        total_size = docs.aggregate(s=Sum('file_size'))['s'] or 0
        cat_stats.append({
            'category': cat,
            'count': docs.count(),
            'total_size': total_size,
            'total_size_display': Document.objects.none() and '0 o' or _format_cat_size(total_size),
        })

    context = {
        'stats': stats,
        'cat_stats': cat_stats,
    }
    return render(request, 'documents/document_stats.html', context)


def _format_cat_size(size):
    if size < 1024:
        return f"{size} o"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} Ko"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} Mo"
    return f"{size / (1024 * 1024 * 1024):.2f} Go"
