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

