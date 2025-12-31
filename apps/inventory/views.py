from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Equipment, Category


@login_required
def equipment_list(request):
    """Liste des équipements."""
    equipment = Equipment.objects.select_related('category', 'responsible').all()
    categories = Category.objects.all()
    
    category_filter = request.GET.get('category')
    if category_filter:
        equipment = equipment.filter(category_id=category_filter)
    
    condition_filter = request.GET.get('condition')
    if condition_filter:
        equipment = equipment.filter(condition=condition_filter)
    
    context = {
        'equipment': equipment,
        'categories': categories,
        'conditions': Equipment.Condition.choices,
    }
    return render(request, 'inventory/equipment_list.html', context)

