from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from apps.core.permissions import role_required
from apps.core.models import AuditLog
from .models import Equipment, Category
from .forms import EquipmentForm


@login_required
@role_required('admin', 'secretariat')
def equipment_list(request):
    """Liste des équipements."""
    equipment = Equipment.active.select_related('category', 'responsible').all()
    categories = Category.objects.all()
    
    category_filter = request.GET.get('category')
    if category_filter:
        equipment = equipment.filter(category_id=category_filter)
    
    condition_filter = request.GET.get('condition')
    if condition_filter:
        equipment = equipment.filter(condition=condition_filter)
    
    # Filtre pour les équipements nécessitant une attention
    attention_filter = request.GET.get('needs_attention')
    if attention_filter == '1':
        equipment = equipment.filter(condition__in=[Equipment.Condition.MAINTENANCE, Equipment.Condition.BROKEN])
    
    # Statistiques pour les badges
    total_equipment = Equipment.active.count()
    needs_attention_count = Equipment.active.filter(
        condition__in=[Equipment.Condition.MAINTENANCE, Equipment.Condition.BROKEN]
    ).count()
    
    context = {
        'equipment': equipment,
        'categories': categories,
        'conditions': Equipment.Condition.choices,
        'total_equipment': total_equipment,
        'needs_attention_count': needs_attention_count,
        'current_filters': {
            'category': category_filter,
            'condition': condition_filter,
            'needs_attention': attention_filter,
        }
    }
    return render(request, 'inventory/equipment_list.html', context)


@login_required
@role_required('admin', 'secretariat')
def equipment_create(request):
    """Création d'un nouvel équipement."""
    if request.method == 'POST':
        form = EquipmentForm(request.POST, request.FILES)
        if form.is_valid():
            equipment = form.save()
            
            # Logger la création dans l'audit
            AuditLog.log_from_request(
                request=request,
                action=AuditLog.Action.CREATE,
                model_name='Equipment',
                object_id=equipment.pk,
                object_repr=str(equipment),
                extra_data={
                    'equipment_name': equipment.name,
                    'category': str(equipment.category) if equipment.category else None,
                    'condition': equipment.condition
                }
            )
            
            messages.success(request, f'Équipement "{equipment.name}" créé avec succès.')
            return redirect('inventory:detail', pk=equipment.pk)
    else:
        form = EquipmentForm()
    
    context = {
        'form': form,
        'title': 'Nouvel équipement',
        'submit_text': 'Créer l\'équipement'
    }
    return render(request, 'inventory/equipment_form.html', context)


@login_required
@role_required('admin', 'secretariat')
def equipment_detail(request, pk):
    """Détail d'un équipement."""
    equipment = get_object_or_404(Equipment.active, pk=pk)
    
    # Récupérer l'historique des modifications
    audit_logs = AuditLog.objects.filter(
        model_name='Equipment',
        object_id=str(pk)
    ).select_related('user').order_by('-timestamp')[:10]  # 10 dernières entrées
    
    context = {
        'equipment': equipment,
        'audit_logs': audit_logs,
    }
    return render(request, 'inventory/equipment_detail.html', context)


@login_required
@role_required('admin', 'secretariat')
def equipment_update(request, pk):
    """Modification d'un équipement."""
    equipment = get_object_or_404(Equipment.active, pk=pk)
    
    if request.method == 'POST':
        form = EquipmentForm(request.POST, request.FILES, instance=equipment)
        if form.is_valid():
            # Capturer les changements avant la sauvegarde
            changes = {}
            for field in form.changed_data:
                old_value = getattr(equipment, field)
                new_value = form.cleaned_data[field]
                
                # Gérer les cas spéciaux (ForeignKey, etc.)
                if hasattr(old_value, 'pk'):
                    old_value = str(old_value)
                if hasattr(new_value, 'pk'):
                    new_value = str(new_value)
                
                changes[field] = {
                    'old': str(old_value) if old_value is not None else None,
                    'new': str(new_value) if new_value is not None else None
                }
            
            equipment = form.save()
            
            # Logger la modification dans l'audit
            if changes:
                AuditLog.log_from_request(
                    request=request,
                    action=AuditLog.Action.UPDATE,
                    model_name='Equipment',
                    object_id=equipment.pk,
                    object_repr=str(equipment),
                    changes=changes,
                    extra_data={
                        'equipment_name': equipment.name,
                        'fields_changed': list(changes.keys())
                    }
                )
            
            messages.success(request, f'Équipement "{equipment.name}" modifié avec succès.')
            return redirect('inventory:detail', pk=equipment.pk)
    else:
        form = EquipmentForm(instance=equipment)
    
    context = {
        'form': form,
        'equipment': equipment,
        'title': f'Modifier {equipment.name}',
        'submit_text': 'Enregistrer les modifications'
    }
    return render(request, 'inventory/equipment_form.html', context)


@login_required
@role_required('admin', 'secretariat')
def equipment_delete(request, pk):
    """Suppression (soft delete) d'un équipement."""
    equipment = get_object_or_404(Equipment.active, pk=pk)
    
    if request.method == 'POST':
        equipment_name = equipment.name
        equipment.soft_delete()
        
        # Logger la suppression dans l'audit
        AuditLog.log_from_request(
            request=request,
            action=AuditLog.Action.DELETE,
            model_name='Equipment',
            object_id=equipment.pk,
            object_repr=equipment_name,
            extra_data={
                'equipment_name': equipment_name,
                'soft_delete': True,
                'category': str(equipment.category) if equipment.category else None
            }
        )
        
        messages.success(request, f'Équipement "{equipment_name}" supprimé avec succès.')
        return redirect('inventory:list')
    
    context = {
        'equipment': equipment,
    }
    return render(request, 'inventory/equipment_delete_confirm.html', context)


# =============================================================================
# CRUD POUR LES CATÉGORIES D'ÉQUIPEMENT
# =============================================================================

@login_required
@role_required('admin', 'secretariat')
def category_list(request):
    """Liste des catégories d'équipement."""
    categories = Category.objects.all().order_by('name')
    
    # Statistiques d'utilisation
    for category in categories:
        category.equipment_count = category.equipment_set.filter(is_deleted=False).count()
        category.active_equipment_count = category.equipment_set.filter(
            is_deleted=False,
            condition__in=[Equipment.Condition.EXCELLENT, Equipment.Condition.GOOD]
        ).count()
    
    context = {
        'categories': categories,
        'total_categories': categories.count(),
    }
    
    return render(request, 'inventory/category_list.html', context)


@login_required
@role_required('admin', 'secretariat')
def category_create(request):
    """Créer une nouvelle catégorie d'équipement."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not name:
            messages.error(request, 'Le nom de la catégorie est requis.')
        else:
            # Vérifier l'unicité
            if Category.objects.filter(name__iexact=name).exists():
                messages.error(request, f'Une catégorie "{name}" existe déjà.')
            else:
                category = Category.objects.create(
                    name=name,
                    description=description
                )
                
                # Logger la création
                AuditLog.log_from_request(
                    request=request,
                    action=AuditLog.Action.CREATE,
                    model_name='Category',
                    object_id=category.pk,
                    object_repr=str(category),
                    extra_data={'category_name': category.name}
                )
                
                messages.success(request, f'Catégorie "{category.name}" créée avec succès.')
                return redirect('inventory:category_list')
    
    context = {
        'title': 'Nouvelle catégorie',
        'submit_text': 'Créer la catégorie'
    }
    return render(request, 'inventory/category_form.html', context)


@login_required
@role_required('admin', 'secretariat')
def category_update(request, pk):
    """Modifier une catégorie d'équipement."""
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not name:
            messages.error(request, 'Le nom de la catégorie est requis.')
        else:
            # Vérifier l'unicité (exclure la catégorie actuelle)
            if Category.objects.filter(name__iexact=name).exclude(pk=pk).exists():
                messages.error(request, f'Une catégorie "{name}" existe déjà.')
            else:
                old_name = category.name
                category.name = name
                category.description = description
                category.save()
                
                # Logger la modification
                AuditLog.log_from_request(
                    request=request,
                    action=AuditLog.Action.UPDATE,
                    model_name='Category',
                    object_id=category.pk,
                    object_repr=str(category),
                    changes={
                        'name': {'old': old_name, 'new': name}
                    } if old_name != name else {},
                    extra_data={'category_name': category.name}
                )
                
                messages.success(request, f'Catégorie "{category.name}" modifiée avec succès.')
                return redirect('inventory:category_list')
    
    context = {
        'category': category,
        'title': f'Modifier {category.name}',
        'submit_text': 'Enregistrer les modifications'
    }
    return render(request, 'inventory/category_form.html', context)


@login_required
@role_required('admin', 'secretariat')
def category_delete(request, pk):
    """Supprimer une catégorie d'équipement."""
    category = get_object_or_404(Category, pk=pk)
    
    # Vérifier s'il y a des équipements liés
    equipment_count = category.equipment_set.filter(is_deleted=False).count()
    
    if request.method == 'POST':
        if equipment_count > 0:
            # Demander confirmation pour la réassignation
            reassign_to_id = request.POST.get('reassign_to')
            if reassign_to_id:
                try:
                    new_category = Category.objects.get(pk=reassign_to_id)
                    category.equipment_set.filter(is_deleted=False).update(category=new_category)
                    messages.success(
                        request, 
                        f'{equipment_count} équipement(s) réassigné(s) à "{new_category.name}".'
                    )
                except Category.DoesNotExist:
                    messages.error(request, 'Catégorie de réassignation invalide.')
                    return redirect('inventory:category_delete', pk=pk)
            else:
                # Supprimer la catégorie des équipements (mettre à null)
                category.equipment_set.filter(is_deleted=False).update(category=None)
                messages.warning(
                    request, 
                    f'{equipment_count} équipement(s) n\'ont plus de catégorie.'
                )
        
        category_name = category.name
        
        # Logger la suppression
        AuditLog.log_from_request(
            request=request,
            action=AuditLog.Action.DELETE,
            model_name='Category',
            object_id=category.pk,
            object_repr=category_name,
            extra_data={
                'category_name': category_name,
                'equipment_count': equipment_count
            }
        )
        
        category.delete()
        messages.success(request, f'Catégorie "{category_name}" supprimée avec succès.')
        return redirect('inventory:category_list')
    
    # Autres catégories pour réassignation
    other_categories = Category.objects.exclude(pk=pk)
    
    context = {
        'category': category,
        'equipment_count': equipment_count,
        'other_categories': other_categories,
    }
    return render(request, 'inventory/category_delete_confirm.html', context)

