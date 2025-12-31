from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Department


@login_required
def department_list(request):
    """Liste des départements."""
    departments = Department.objects.filter(is_active=True)
    return render(request, 'departments/department_list.html', {'departments': departments})


@login_required
def department_detail(request, pk):
    """Détail d'un département."""
    department = get_object_or_404(Department, pk=pk)
    return render(request, 'departments/department_detail.html', {'department': department})

