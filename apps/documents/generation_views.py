"""Vues de l'éditeur de documents générés (compte-rendu, courrier, etc.)."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from apps.core.permissions import role_required
from .forms import GeneratedDocumentForm
from .generation import render_generated_document_pdf
from .models import Document, GeneratedDocument


GENERATOR_ROLES = ('admin', 'secretariat', 'pasteur', 'ancien', 'diacre', 'finance', 'encadrant')


def _user_can_generate(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or getattr(user, 'is_admin', False):
        return True
    return hasattr(user, 'has_any_role') and user.has_any_role(*GENERATOR_ROLES)


@login_required
def generated_list(request):
    user = request.user

    qs = GeneratedDocument.objects.select_related('created_by', 'generated_document').all()

    # Filtrage par accès
    if not (user.is_superuser or getattr(user, 'is_admin', False)
            or (hasattr(user, 'has_any_role') and user.has_any_role('admin', 'secretariat'))):
        accessible_ids = [d.pk for d in qs if d.can_be_accessed_by(user)]
        qs = qs.filter(pk__in=accessible_ids)

    kind = request.GET.get('kind')
    status = request.GET.get('status')
    search = request.GET.get('q')
    if kind:
        qs = qs.filter(kind=kind)
    if status:
        qs = qs.filter(status=status)
    if search:
        from django.db.models import Q
        qs = qs.filter(Q(title__icontains=search) | Q(reference__icontains=search) | Q(subject__icontains=search))

    page = Paginator(qs, 20).get_page(request.GET.get('page'))

    return render(request, 'documents/generated/list.html', {
        'page_obj': page,
        'kinds': GeneratedDocument.Kind.choices,
        'statuses': GeneratedDocument.Status.choices,
        'current_kind': kind or '',
        'current_status': status or '',
        'search': search or '',
        'can_generate': _user_can_generate(user),
    })


@login_required
def generated_create(request):
    if not _user_can_generate(request.user):
        messages.error(request, "Vous n'avez pas les droits pour créer un document.")
        return redirect('documents:generated_list')

    initial = {
        'document_date': timezone.now().date(),
        'signature_name': request.user.get_full_name() or request.user.username,
        'kind': request.GET.get('kind') or GeneratedDocument.Kind.COURRIER,
    }

    if request.method == 'POST':
        form = GeneratedDocumentForm(request.POST)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.created_by = request.user
            if not doc.reference:
                doc.reference = doc.generate_reference()
            doc.save()
            messages.success(request, f"Brouillon « {doc.title} » enregistré.")
            if request.POST.get('action') == 'finalize':
                document = _finalize_generated_document(request, doc)
                messages.success(request, "Document finalisé et ajouté à la bibliothèque.")
                return redirect('documents:detail', pk=document.pk)
            return redirect('documents:generated_edit', pk=doc.pk)
    else:
        form = GeneratedDocumentForm(initial=initial)

    return render(request, 'documents/generated/editor.html', {
        'form': form,
        'doc': None,
        'mode': 'create',
    })


@login_required
def generated_edit(request, pk):
    doc = get_object_or_404(GeneratedDocument, pk=pk)
    if not (request.user == doc.created_by or _user_can_generate(request.user)):
        raise Http404
    if doc.status == GeneratedDocument.Status.FINALIZED and not (
        request.user.is_superuser or getattr(request.user, 'is_admin', False)
    ):
        messages.warning(request, "Ce document est finalisé, créez une copie pour modifier.")
        return redirect('documents:generated_preview', pk=doc.pk)

    if request.method == 'POST':
        form = GeneratedDocumentForm(request.POST, instance=doc)
        if form.is_valid():
            saved = form.save(commit=False)
            if not saved.reference:
                saved.reference = saved.generate_reference()
            saved.save()
            messages.success(request, "Document mis à jour.")
            if request.POST.get('action') == 'finalize':
                document = _finalize_generated_document(request, saved)
                messages.success(request, "Document finalisé et ajouté à la bibliothèque.")
                return redirect('documents:detail', pk=document.pk)
            return redirect('documents:generated_edit', pk=saved.pk)
    else:
        form = GeneratedDocumentForm(instance=doc)

    return render(request, 'documents/generated/editor.html', {
        'form': form,
        'doc': doc,
        'mode': 'edit',
    })


@login_required
def generated_preview(request, pk):
    doc = get_object_or_404(GeneratedDocument, pk=pk)
    if not doc.can_be_accessed_by(request.user):
        raise Http404
    return render(request, 'documents/generated/preview.html', {'doc': doc})


@login_required
def generated_pdf(request, pk):
    doc = get_object_or_404(GeneratedDocument, pk=pk)
    if not doc.can_be_accessed_by(request.user):
        raise Http404
    pdf_bytes = render_generated_document_pdf(doc)
    safe_name = slugify(doc.title) or f'document-{doc.pk}'
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{safe_name}.pdf"'
    return response


def _finalize_generated_document(request, doc):
    pdf_bytes = render_generated_document_pdf(doc)
    safe_name = slugify(doc.title) or f'document-{doc.pk}'
    file_name = f'{safe_name}.pdf'

    if doc.generated_document:
        document = doc.generated_document
        document.file.save(file_name, ContentFile(pdf_bytes), save=False)
        document.title = doc.title
        document.file_name = file_name
        document.file_size = len(pdf_bytes)
        document.file_type = 'application/pdf'
        document.media_type = Document.MediaType.DOCUMENT
        document.source = Document.Source.GENERATED
        document.visibility = doc.visibility
        document.allowed_roles = doc.allowed_roles
        document.uploaded_by = request.user
        document.save()
    else:
        document = Document(
            title=doc.title,
            description=doc.subject or doc.get_kind_display(),
            file_name=file_name,
            file_size=len(pdf_bytes),
            file_type='application/pdf',
            media_type=Document.MediaType.DOCUMENT,
            source=Document.Source.GENERATED,
            visibility=doc.visibility,
            allowed_roles=doc.allowed_roles,
            uploaded_by=request.user,
            tags=doc.kind,
        )
        document.file.save(file_name, ContentFile(pdf_bytes), save=False)
        document.save()
        doc.generated_document = document

    doc.status = GeneratedDocument.Status.FINALIZED
    doc.save()
    return document


@login_required
@require_POST
def generated_finalize(request, pk):
    doc = get_object_or_404(GeneratedDocument, pk=pk)
    if not (request.user == doc.created_by or _user_can_generate(request.user)):
        raise Http404
    document = _finalize_generated_document(request, doc)
    messages.success(request, "Document finalisé et ajouté à la bibliothèque.")
    return redirect('documents:detail', pk=document.pk)


@login_required
@require_POST
def generated_delete(request, pk):
    doc = get_object_or_404(GeneratedDocument, pk=pk)
    if not (request.user == doc.created_by or request.user.is_superuser
            or getattr(request.user, 'is_admin', False)):
        raise Http404
    title = doc.title
    doc.delete()
    messages.success(request, f"Document « {title} » supprimé.")
    return redirect('documents:generated_list')


# ----- Modèles de contenu prêt-à-l'emploi -----
KIND_TEMPLATES = {
    'compte_rendu': """<p><strong>Date de la réunion :</strong> ___________</p>
<p><strong>Lieu :</strong> ___________</p>
<p><strong>Participants :</strong> ___________</p>
<p><strong>Excusés :</strong> ___________</p>
<h3>1. Ouverture</h3><p>...</p>
<h3>2. Ordre du jour</h3><ol><li>...</li></ol>
<h3>3. Décisions prises</h3><p>...</p>
<h3>4. Actions à mener</h3><p>...</p>
<h3>5. Clôture</h3><p>...</p>""",
    'courrier': """<p>Madame, Monsieur,</p>
<p>...</p>
<p>Veuillez agréer, Madame, Monsieur, l'expression de nos salutations distinguées.</p>""",
    'convocation': """<p>Cher frère, chère sœur,</p>
<p>Nous avons l'honneur de vous convoquer à <strong>...</strong> qui se tiendra le <strong>...</strong> à <strong>...</strong>, dans les locaux de notre église.</p>
<p><strong>Ordre du jour :</strong></p><ol><li>...</li></ol>
<p>Votre présence est vivement souhaitée.</p>""",
    'attestation': """<p>Je soussigné(e), <strong>...</strong>, atteste par la présente que <strong>...</strong> est membre régulier de notre église depuis le <strong>...</strong>.</p>
<p>La présente attestation est délivrée à l'intéressé(e) pour servir et valoir ce que de droit.</p>""",
    'note_service': """<p><strong>À l'attention de :</strong> ...</p>
<p><strong>Référence :</strong> ...</p>
<p>Par la présente note, ...</p>""",
    'rapport': """<h3>1. Contexte</h3><p>...</p>
<h3>2. Activités réalisées</h3><p>...</p>
<h3>3. Résultats</h3><p>...</p>
<h3>4. Difficultés rencontrées</h3><p>...</p>
<h3>5. Perspectives</h3><p>...</p>""",
    'autre': "<p>...</p>",
}


@login_required
def generated_template_snippet(request):
    """Renvoie un snippet HTML de modèle pour le type demandé."""
    kind = request.GET.get('kind', 'autre')
    return JsonResponse({'html': KIND_TEMPLATES.get(kind, KIND_TEMPLATES['autre'])})
