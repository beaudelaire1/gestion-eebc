"""Vues pour le module Worship."""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from datetime import date, timedelta

from .models import WorshipService, ServiceRole, ServicePlanItem, ServiceTemplate
from .forms import WorshipServiceForm, ServiceRoleForm, ServicePlanItemForm


@login_required
def service_list(request):
    """Liste des services de culte."""
    services = WorshipService.objects.select_related('event').prefetch_related(
        'roles', 'roles__member'
    ).order_by('-event__start_date')
    
    # Filtres
    upcoming_only = request.GET.get('upcoming', 'true') == 'true'
    if upcoming_only:
        services = services.filter(event__start_date__gte=date.today())
    
    context = {
        'services': services,
        'upcoming_only': upcoming_only,
    }
    
    return render(request, 'worship/service_list.html', context)


@login_required
def service_detail(request, pk):
    """Détail d'un service de culte."""
    service = get_object_or_404(
        WorshipService.objects.select_related('event').prefetch_related(
            'roles', 'roles__member', 'plan_items', 'plan_items__responsible'
        ),
        pk=pk
    )
    
    context = {
        'service': service,
        'roles': service.roles.all(),
        'plan_items': service.plan_items.all().order_by('order', 'start_time'),
    }
    
    return render(request, 'worship/service_detail.html', context)


@login_required
def service_create(request):
    """Créer un nouveau service."""
    if request.method == 'POST':
        form = WorshipServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.created_by = request.user
            service.save()
            messages.success(request, "Service créé avec succès.")
            return redirect('worship:service_detail', pk=service.pk)
    else:
        form = WorshipServiceForm()
    
    return render(request, 'worship/service_form.html', {'form': form})


@login_required
def service_edit(request, pk):
    """Modifier un service."""
    service = get_object_or_404(WorshipService, pk=pk)
    
    if request.method == 'POST':
        form = WorshipServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, "Service mis à jour.")
            return redirect('worship:service_detail', pk=pk)
    else:
        form = WorshipServiceForm(instance=service)
    
    return render(request, 'worship/service_form.html', {'form': form, 'service': service})


@login_required
@require_POST
def role_assign(request, service_pk):
    """Assigner un membre à un rôle (HTMX)."""
    service = get_object_or_404(WorshipService, pk=service_pk)
    
    role_type = request.POST.get('role')
    member_id = request.POST.get('member_id')
    
    if not role_type:
        return JsonResponse({'error': 'Rôle requis'}, status=400)
    
    from apps.members.models import Member
    member = get_object_or_404(Member, pk=member_id) if member_id else None
    
    role, created = ServiceRole.objects.update_or_create(
        service=service,
        role=role_type,
        defaults={
            'member': member,
            'status': ServiceRole.Status.EN_ATTENTE if member else ServiceRole.Status.EN_ATTENTE
        }
    )
    
    if request.headers.get('HX-Request'):
        html = render_to_string('worship/partials/role_row.html', {
            'role': role,
            'service': service
        }, request=request)
        return HttpResponse(html)
    
    return redirect('worship:service_detail', pk=service_pk)


@login_required
@require_POST
def role_confirm(request, pk):
    """Confirmer un rôle (HTMX)."""
    role = get_object_or_404(ServiceRole, pk=pk)
    role.confirm()
    
    if request.headers.get('HX-Request'):
        html = render_to_string('worship/partials/role_row.html', {
            'role': role,
            'service': role.service
        }, request=request)
        return HttpResponse(html)
    
    return redirect('worship:service_detail', pk=role.service.pk)


@login_required
@require_POST
def role_decline(request, pk):
    """Décliner un rôle (HTMX)."""
    role = get_object_or_404(ServiceRole, pk=pk)
    role.decline()
    
    if request.headers.get('HX-Request'):
        html = render_to_string('worship/partials/role_row.html', {
            'role': role,
            'service': role.service
        }, request=request)
        return HttpResponse(html)
    
    return redirect('worship:service_detail', pk=role.service.pk)


@login_required
def plan_edit(request, service_pk):
    """Éditer le déroulement d'un service."""
    service = get_object_or_404(WorshipService, pk=service_pk)
    plan_items = service.plan_items.all().order_by('order', 'start_time')
    
    context = {
        'service': service,
        'plan_items': plan_items,
        'item_types': ServicePlanItem.ItemType.choices,
    }
    
    return render(request, 'worship/plan_edit.html', context)


@login_required
@require_POST
def plan_item_add(request, service_pk):
    """Ajouter un élément au programme (HTMX)."""
    service = get_object_or_404(WorshipService, pk=service_pk)
    
    form = ServicePlanItemForm(request.POST)
    if form.is_valid():
        item = form.save(commit=False)
        item.service = service
        # Auto-incrémenter l'ordre
        max_order = service.plan_items.aggregate(
            max_order=models.Max('order')
        )['max_order'] or 0
        item.order = max_order + 1
        item.save()
        
        if request.headers.get('HX-Request'):
            html = render_to_string('worship/partials/plan_item_row.html', {
                'item': item
            }, request=request)
            return HttpResponse(html)
    
    return redirect('worship:plan_edit', service_pk=service_pk)


@login_required
def run_sheet_pdf(request, pk):
    """Génère la fiche de déroulement PDF."""
    service = get_object_or_404(
        WorshipService.objects.select_related('event').prefetch_related(
            'roles', 'roles__member', 'plan_items', 'plan_items__responsible'
        ),
        pk=pk
    )
    
    # Utiliser WeasyPrint pour générer le PDF
    from django.template.loader import get_template
    from weasyprint import HTML
    
    template = get_template('worship/pdf/run_sheet.html')
    html_content = template.render({
        'service': service,
        'roles': service.roles.filter(status='confirme'),
        'plan_items': service.plan_items.all().order_by('order', 'start_time'),
    })
    
    pdf = HTML(string=html_content).write_pdf()
    
    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f"run_sheet_{service.event.start_date.strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    
    return response


@login_required
def apply_template(request, service_pk, template_pk):
    """Applique un modèle de service."""
    service = get_object_or_404(WorshipService, pk=service_pk)
    template = get_object_or_404(ServiceTemplate, pk=template_pk)
    
    # Supprimer les éléments existants
    service.plan_items.all().delete()
    
    # Copier les éléments du modèle
    for template_item in template.items.all():
        ServicePlanItem.objects.create(
            service=service,
            item_type=template_item.item_type,
            title=template_item.title,
            order=template_item.order,
            duration_minutes=template_item.duration_minutes,
            notes=template_item.notes,
        )
    
    messages.success(request, f"Modèle '{template.name}' appliqué.")
    return redirect('worship:plan_edit', service_pk=service_pk)
