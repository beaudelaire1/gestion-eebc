from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from apps.core.permissions import role_required
from apps.members.models import Member
from .models import Department
from .forms import DepartmentForm, DepartmentMembersForm


@login_required
def department_list(request):
    """Liste des départements."""
    departments = Department.objects.filter(is_active=True)
    return render(request, 'departments/department_list.html', {'departments': departments})


@login_required
def department_detail(request, pk):
    """
    Détail d'un département avec liste complète des membres.
    Requirements: 12.4
    """
    department = get_object_or_404(Department, pk=pk)
    
    # Récupérer les membres avec informations supplémentaires
    members = department.members.filter(status=Member.Status.ACTIF).select_related().order_by('last_name', 'first_name')
    
    # Statistiques du département
    stats = {
        'total_members': members.count(),
        'active_members': members.filter(status=Member.Status.ACTIF).count(),
        'has_phone': members.exclude(phone__isnull=True).exclude(phone='').count(),
        'has_email': members.exclude(email__isnull=True).exclude(email='').count(),
    }
    
    return render(request, 'departments/department_detail.html', {
        'department': department,
        'members': members,
        'stats': stats
    })


@login_required
@role_required('admin', 'secretariat')
def department_create(request):
    """
    Créer un nouveau département.
    Requirements: 12.1
    """
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            department = form.save()
            messages.success(request, f'Le département "{department.name}" a été créé avec succès.')
            return redirect('departments:detail', pk=department.pk)
    else:
        form = DepartmentForm()
    
    return render(request, 'departments/department_form.html', {
        'form': form,
        'title': 'Créer un département',
        'submit_text': 'Créer'
    })


@login_required
@role_required('admin', 'secretariat')
def department_update(request, pk):
    """
    Modifier un département existant.
    Requirements: 12.2
    """
    department = get_object_or_404(Department, pk=pk)
    
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            department = form.save()
            messages.success(request, f'Le département "{department.name}" a été modifié avec succès.')
            return redirect('departments:detail', pk=department.pk)
    else:
        form = DepartmentForm(instance=department)
    
    return render(request, 'departments/department_form.html', {
        'form': form,
        'department': department,
        'title': f'Modifier {department.name}',
        'submit_text': 'Modifier'
    })


@login_required
@role_required('admin', 'secretariat')
def department_members(request, pk):
    """
    Gérer les membres d'un département.
    Requirements: 12.3
    """
    department = get_object_or_404(Department, pk=pk)
    
    if request.method == 'POST':
        form = DepartmentMembersForm(request.POST, department=department)
        if form.is_valid():
            with transaction.atomic():
                # Supprimer tous les membres actuels
                department.members.clear()
                # Ajouter les nouveaux membres sélectionnés
                selected_members = form.cleaned_data['members']
                department.members.set(selected_members)
            
            messages.success(
                request, 
                f'Les membres du département "{department.name}" ont été mis à jour. '
                f'{selected_members.count()} membre(s) assigné(s).'
            )
            return redirect('departments:detail', pk=department.pk)
    else:
        form = DepartmentMembersForm(department=department)
    
    return render(request, 'departments/department_members.html', {
        'form': form,
        'department': department,
        'current_members': department.members.all()
    })


@login_required
@role_required('admin', 'secretariat')
def department_delete(request, pk):
    """
    Supprimer un département (soft delete).
    Requirements: 12.5
    """
    department = get_object_or_404(Department, pk=pk)
    
    # Vérifier s'il y a des membres assignés
    members_count = department.members.count()
    
    if request.method == 'POST':
        department_name = department.name
        
        # Soft delete - marquer comme inactif
        department.is_active = False
        department.save()
        
        # Les membres restent dans le système mais ne sont plus assignés au département
        if members_count > 0:
            department.members.clear()
            messages.info(request, f'{members_count} membre(s) retiré(s) du département.')
        
        messages.success(request, f'Département "{department_name}" supprimé avec succès.')
        return redirect('departments:list')
    
    context = {
        'department': department,
        'members_count': members_count,
    }
    return render(request, 'departments/department_delete_confirm.html', context)

