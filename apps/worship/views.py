"""Vues pour le module Worship."""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.db import models
from datetime import date, timedelta

from .models import WorshipService, ServiceRole, ServicePlanItem, ServiceTemplate, ServiceTemplateItem
from .forms import WorshipServiceForm, ServiceRoleForm, ServicePlanItemForm
from apps.core.permissions import role_required


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
@role_required('admin', 'responsable_groupe')
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
@role_required('admin', 'responsable_groupe')
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
@role_required('admin', 'responsable_groupe')
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
@role_required('admin', 'responsable_groupe')
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
@role_required('admin', 'responsable_groupe')
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
@role_required('admin', 'responsable_groupe')
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


# =============================================================================
# PLANIFICATION MENSUELLE DES CULTES
# =============================================================================

from .models import MonthlySchedule, ScheduledService, ServiceNotification


@login_required
def monthly_schedule_list(request):
    """Liste des plannings mensuels."""
    schedules = MonthlySchedule.objects.select_related('site', 'created_by').order_by('-year', '-month')
    
    # Filtre par site
    site_id = request.GET.get('site')
    if site_id:
        schedules = schedules.filter(site_id=site_id)
    
    # Filtre par année
    year = request.GET.get('year')
    if year:
        schedules = schedules.filter(year=year)
    
    from apps.core.models import Site
    
    context = {
        'schedules': schedules,
        'sites': Site.objects.filter(is_active=True),
        'years': MonthlySchedule.objects.values_list('year', flat=True).distinct().order_by('-year'),
        'selected_site': site_id,
        'selected_year': year,
    }
    
    return render(request, 'worship/schedule_list.html', context)


@login_required
@role_required('admin', 'responsable_groupe')
def monthly_schedule_create(request):
    """Créer un nouveau planning mensuel."""
    from apps.core.models import Site
    from datetime import date
    
    if request.method == 'POST':
        year = int(request.POST.get('year'))
        month = int(request.POST.get('month'))
        site_id = request.POST.get('site')
        
        schedule, created = MonthlySchedule.objects.get_or_create(
            year=year,
            month=month,
            site_id=site_id,
            defaults={
                'created_by': request.user,
                'status': 'brouillon'
            }
        )
        
        if created:
            messages.success(request, f"Planning {schedule} créé avec succès.")
        else:
            messages.info(request, f"Le planning {schedule} existe déjà.")
        
        return redirect('worship:schedule_detail', pk=schedule.pk)
    
    today = date.today()
    
    context = {
        'sites': Site.objects.filter(is_active=True),
        'current_year': today.year,
        'current_month': today.month,
        'months': [
            (1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'),
            (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'),
            (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre')
        ],
        'years': range(today.year, today.year + 3),
    }
    
    return render(request, 'worship/schedule_create.html', context)


@login_required
def monthly_schedule_detail(request, pk):
    """Détail d'un planning mensuel avec tous les cultes."""
    schedule = get_object_or_404(
        MonthlySchedule.objects.select_related('site').prefetch_related(
            'services', 'services__preacher', 'services__worship_leader',
            'services__choir_leader', 'services__singers', 'services__musicians'
        ),
        pk=pk
    )
    
    context = {
        'schedule': schedule,
        'services': schedule.services.all().order_by('date'),
    }
    
    return render(request, 'worship/schedule_detail.html', context)


@login_required
@role_required('admin', 'responsable_groupe')
def monthly_schedule_edit(request, pk):
    """Modifier les paramètres d'un planning."""
    schedule = get_object_or_404(MonthlySchedule, pk=pk)
    
    if request.method == 'POST':
        schedule.notification_day = int(request.POST.get('notification_day', 3))
        schedule.days_before_service = int(request.POST.get('days_before_service', 4))
        schedule.notify_by_email = 'notify_by_email' in request.POST
        schedule.notify_by_sms = 'notify_by_sms' in request.POST
        schedule.notify_by_whatsapp = 'notify_by_whatsapp' in request.POST
        schedule.notes = request.POST.get('notes', '')
        schedule.save()
        
        messages.success(request, "Planning mis à jour.")
        return redirect('worship:schedule_detail', pk=pk)
    
    context = {
        'schedule': schedule,
        'days': [
            (0, 'Lundi'), (1, 'Mardi'), (2, 'Mercredi'), (3, 'Jeudi'),
            (4, 'Vendredi'), (5, 'Samedi'), (6, 'Dimanche')
        ],
    }
    
    return render(request, 'worship/schedule_edit.html', context)


@login_required
@role_required('admin', 'responsable_groupe')
def generate_sundays(request, pk):
    """Génère les cultes pour tous les dimanches du mois."""
    schedule = get_object_or_404(MonthlySchedule, pk=pk)
    
    sundays = schedule.get_sundays()
    created = 0
    
    for sunday in sundays:
        _, was_created = ScheduledService.objects.get_or_create(
            schedule=schedule,
            date=sunday,
            defaults={'start_time': '09:30'}
        )
        if was_created:
            created += 1
    
    messages.success(request, f"{created} culte(s) créé(s) pour {schedule.month_name} {schedule.year}")
    return redirect('worship:schedule_detail', pk=pk)


@login_required
@role_required('admin', 'responsable_groupe')
def publish_schedule(request, pk):
    """Publie le planning."""
    schedule = get_object_or_404(MonthlySchedule, pk=pk)
    schedule.publish()
    messages.success(request, f"Planning {schedule} publié !")
    return redirect('worship:schedule_detail', pk=pk)


@login_required
@role_required('admin', 'responsable_groupe')
def send_notifications(request, pk):
    """Envoie les notifications pour tous les cultes."""
    schedule = get_object_or_404(MonthlySchedule, pk=pk)
    
    sent = 0
    for service in schedule.services.filter(notifications_sent=False):
        try:
            service.send_notifications()
            sent += 1
        except Exception as e:
            messages.error(request, f"Erreur pour {service}: {e}")
    
    if sent:
        messages.success(request, f"Notifications envoyées pour {sent} culte(s)")
    else:
        messages.info(request, "Aucune notification à envoyer")
    
    return redirect('worship:schedule_detail', pk=pk)


@login_required
def scheduled_service_detail(request, pk):
    """Détail d'un culte programmé."""
    service = get_object_or_404(
        ScheduledService.objects.select_related(
            'schedule', 'schedule__site', 'preacher', 'worship_leader', 
            'choir_leader', 'sound_tech', 'projection'
        ).prefetch_related('singers', 'musicians'),
        pk=pk
    )
    
    context = {
        'service': service,
        'schedule': service.schedule,
        'participants': service.get_all_participants(),
    }
    
    return render(request, 'worship/culte_detail.html', context)


@login_required
@role_required('admin', 'responsable_groupe')
def scheduled_service_edit(request, pk):
    """Modifier un culte programmé."""
    service = get_object_or_404(ScheduledService, pk=pk)
    
    from apps.members.models import Member
    
    if request.method == 'POST':
        service.theme = request.POST.get('theme', '')
        service.bible_text = request.POST.get('bible_text', '')
        service.start_time = request.POST.get('start_time', '09:30')
        service.notes = request.POST.get('notes', '')
        
        # Rôles principaux
        preacher_id = request.POST.get('preacher')
        service.preacher_id = preacher_id if preacher_id else None
        
        leader_id = request.POST.get('worship_leader')
        service.worship_leader_id = leader_id if leader_id else None
        
        choir_id = request.POST.get('choir_leader')
        service.choir_leader_id = choir_id if choir_id else None
        
        sound_id = request.POST.get('sound_tech')
        service.sound_tech_id = sound_id if sound_id else None
        
        projection_id = request.POST.get('projection')
        service.projection_id = projection_id if projection_id else None
        
        # Choristes et musiciens (ManyToMany)
        singers_ids = request.POST.getlist('singers')
        service.singers.set(singers_ids)
        
        musicians_ids = request.POST.getlist('musicians')
        service.musicians.set(musicians_ids)
        
        service.save()
        
        messages.success(request, f"Culte du {service.date.strftime('%d/%m/%Y')} mis à jour.")
        return redirect('worship:schedule_detail', pk=service.schedule.pk)
    
    # Membres pour les sélections
    members = Member.objects.filter(status='actif').order_by('last_name', 'first_name')
    
    context = {
        'service': service,
        'schedule': service.schedule,
        'members': members,
    }
    
    return render(request, 'worship/culte_edit.html', context)


# =============================================================================
# CRUD POUR LES MODÈLES DE SERVICE - OPÉRATIONS MANQUANTES
# =============================================================================

@login_required
@role_required('admin', 'responsable_groupe')
def service_template_list(request):
    """Liste des modèles de service."""
    templates = ServiceTemplate.objects.filter(is_active=True).prefetch_related('items').order_by('name')
    
    # Statistiques
    total_templates = templates.count()
    by_type = {}
    for template in templates:
        service_type = template.get_service_type_display()
        by_type[service_type] = by_type.get(service_type, 0) + 1
    
    context = {
        'templates': templates,
        'total_templates': total_templates,
        'by_type': by_type,
    }
    
    return render(request, 'worship/template_list.html', context)


@login_required
@role_required('admin', 'responsable_groupe')
def service_template_create(request):
    """Créer un nouveau modèle de service."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        service_type = request.POST.get('service_type')
        estimated_duration = request.POST.get('estimated_duration')
        
        if not name:
            messages.error(request, 'Le nom du modèle est requis.')
        else:
            # Vérifier l'unicité
            if ServiceTemplate.objects.filter(name__iexact=name, is_active=True).exists():
                messages.error(request, f'Un modèle "{name}" existe déjà.')
            else:
                try:
                    template = ServiceTemplate.objects.create(
                        name=name,
                        description=description,
                        service_type=service_type,
                        estimated_duration=int(estimated_duration) if estimated_duration else 90,
                        is_active=True
                    )
                    
                    messages.success(request, f'Modèle "{template.name}" créé avec succès.')
                    return redirect('worship:template_detail', pk=template.pk)
                except Exception as e:
                    messages.error(request, f'Erreur lors de la création : {e}')
    
    service_types = WorshipService.ServiceType.choices
    
    context = {
        'service_types': service_types,
        'title': 'Nouveau modèle de service',
        'submit_text': 'Créer le modèle'
    }
    return render(request, 'worship/template_form.html', context)


@login_required
def service_template_detail(request, pk):
    """Détail d'un modèle de service."""
    template = get_object_or_404(
        ServiceTemplate.objects.prefetch_related('items'),
        pk=pk
    )
    
    items = template.items.all().order_by('order')
    
    context = {
        'template': template,
        'items': items,
        'total_duration': sum(item.duration_minutes for item in items),
    }
    
    return render(request, 'worship/template_detail.html', context)


@login_required
@role_required('admin', 'responsable_groupe')
def service_template_update(request, pk):
    """Modifier un modèle de service."""
    template = get_object_or_404(ServiceTemplate, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        service_type = request.POST.get('service_type')
        estimated_duration = request.POST.get('estimated_duration')
        is_active = 'is_active' in request.POST
        
        if not name:
            messages.error(request, 'Le nom du modèle est requis.')
        else:
            # Vérifier l'unicité (exclure le modèle actuel)
            if ServiceTemplate.objects.filter(name__iexact=name, is_active=True).exclude(pk=pk).exists():
                messages.error(request, f'Un modèle "{name}" existe déjà.')
            else:
                try:
                    template.name = name
                    template.description = description
                    template.service_type = service_type
                    template.estimated_duration = int(estimated_duration) if estimated_duration else 90
                    template.is_active = is_active
                    template.save()
                    
                    messages.success(request, f'Modèle "{template.name}" modifié avec succès.')
                    return redirect('worship:template_detail', pk=template.pk)
                except Exception as e:
                    messages.error(request, f'Erreur lors de la modification : {e}')
    
    service_types = WorshipService.ServiceType.choices
    
    context = {
        'template': template,
        'service_types': service_types,
        'title': f'Modifier {template.name}',
        'submit_text': 'Enregistrer les modifications'
    }
    return render(request, 'worship/template_form.html', context)


@login_required
@role_required('admin', 'responsable_groupe')
def service_template_delete(request, pk):
    """Supprimer un modèle de service (soft delete)."""
    template = get_object_or_404(ServiceTemplate, pk=pk)
    
    # Vérifier s'il y a des éléments liés
    items_count = template.items.count()
    
    if request.method == 'POST':
        # Soft delete du modèle
        template_name = template.name
        template.is_active = False
        template.save()
        
        messages.success(request, f'Modèle "{template_name}" supprimé avec succès.')
        return redirect('worship:template_list')
    
    context = {
        'template': template,
        'items_count': items_count,
    }
    return render(request, 'worship/template_delete_confirm.html', context)


# =============================================================================
# CRUD POUR LES ÉLÉMENTS DE MODÈLE - OPÉRATIONS MANQUANTES
# =============================================================================

@login_required
@role_required('admin', 'responsable_groupe')
def template_item_create(request, template_pk):
    """Créer un nouvel élément de modèle."""
    template = get_object_or_404(ServiceTemplate, pk=template_pk)
    
    if request.method == 'POST':
        item_type = request.POST.get('item_type')
        title = request.POST.get('title', '').strip()
        duration_minutes = request.POST.get('duration_minutes')
        notes = request.POST.get('notes', '').strip()
        
        if not item_type:
            messages.error(request, 'Le type d\'élément est requis.')
        else:
            try:
                # Auto-incrémenter l'ordre
                max_order = template.items.aggregate(
                    max_order=models.Max('order')
                )['max_order'] or 0
                
                item = ServiceTemplateItem.objects.create(
                    template=template,
                    item_type=item_type,
                    title=title,
                    order=max_order + 1,
                    duration_minutes=int(duration_minutes) if duration_minutes else 5,
                    notes=notes
                )
                
                messages.success(request, f'Élément "{item.get_item_type_display()}" ajouté avec succès.')
                return redirect('worship:template_detail', pk=template.pk)
            except Exception as e:
                messages.error(request, f'Erreur lors de la création : {e}')
    
    item_types = ServicePlanItem.ItemType.choices
    
    context = {
        'template': template,
        'item_types': item_types,
        'title': f'Nouvel élément - {template.name}',
        'submit_text': 'Ajouter l\'élément'
    }
    return render(request, 'worship/template_item_form.html', context)


@login_required
@role_required('admin', 'responsable_groupe')
def template_item_update(request, pk):
    """Modifier un élément de modèle."""
    item = get_object_or_404(ServiceTemplateItem, pk=pk)
    template = item.template
    
    if request.method == 'POST':
        item_type = request.POST.get('item_type')
        title = request.POST.get('title', '').strip()
        duration_minutes = request.POST.get('duration_minutes')
        notes = request.POST.get('notes', '').strip()
        order = request.POST.get('order')
        
        if not item_type:
            messages.error(request, 'Le type d\'élément est requis.')
        else:
            try:
                item.item_type = item_type
                item.title = title
                item.duration_minutes = int(duration_minutes) if duration_minutes else 5
                item.notes = notes
                item.order = int(order) if order else item.order
                item.save()
                
                messages.success(request, f'Élément "{item.get_item_type_display()}" modifié avec succès.')
                return redirect('worship:template_detail', pk=template.pk)
            except Exception as e:
                messages.error(request, f'Erreur lors de la modification : {e}')
    
    item_types = ServicePlanItem.ItemType.choices
    
    context = {
        'item': item,
        'template': template,
        'item_types': item_types,
        'title': f'Modifier élément - {template.name}',
        'submit_text': 'Enregistrer les modifications'
    }
    return render(request, 'worship/template_item_form.html', context)


@login_required
@role_required('admin', 'responsable_groupe')
def template_item_delete(request, pk):
    """Supprimer un élément de modèle."""
    item = get_object_or_404(ServiceTemplateItem, pk=pk)
    template = item.template
    
    if request.method == 'POST':
        item_type = item.get_item_type_display()
        item.delete()
        
        messages.success(request, f'Élément "{item_type}" supprimé avec succès.')
        return redirect('worship:template_detail', pk=template.pk)
    
    context = {
        'item': item,
        'template': template,
    }
    return render(request, 'worship/template_item_delete_confirm.html', context)


@login_required
@role_required('admin', 'responsable_groupe')
def template_item_reorder(request, template_pk):
    """Réorganiser l'ordre des éléments (HTMX)."""
    template = get_object_or_404(ServiceTemplate, pk=template_pk)
    
    if request.method == 'POST':
        item_ids = request.POST.getlist('item_ids')
        
        for index, item_id in enumerate(item_ids, 1):
            ServiceTemplateItem.objects.filter(
                pk=item_id, 
                template=template
            ).update(order=index)
        
        messages.success(request, 'Ordre des éléments mis à jour.')
    
    return redirect('worship:template_detail', pk=template_pk)