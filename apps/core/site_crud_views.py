"""
Vues CRUD pour la gestion des Sites paroissiaux.
Accessible depuis le tableau de bord interne (/app/sites/).
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

from apps.core.models import Site
from apps.core.forms import SiteForm


@login_required
def site_list(request):
    """Liste de tous les sites."""
    sites = Site.objects.all().select_related('pastor').order_by('-is_main_site', 'name')

    status = request.GET.get('status')
    if status == 'active':
        sites = sites.filter(is_active=True)
    elif status == 'inactive':
        sites = sites.filter(is_active=False)

    context = {
        'sites': sites,
        'active_count': Site.objects.filter(is_active=True).count(),
        'total_count': Site.objects.count(),
    }
    return render(request, 'core/sites/site_list.html', context)


@login_required
def site_detail(request, pk):
    """Détail d'un site."""
    site = get_object_or_404(Site.objects.select_related('pastor'), pk=pk)

    from apps.members.models import Member
    member_count = Member.objects.filter(site=site).count()
    active_member_count = Member.objects.filter(site=site, status=Member.Status.ACTIF).count()

    context = {
        'site': site,
        'member_count': member_count,
        'active_member_count': active_member_count,
        'administrators': site.administrators.all(),
    }
    return render(request, 'core/sites/site_detail.html', context)


@login_required
def site_create(request):
    """Créer un nouveau site."""
    if not (request.user.is_admin or request.user.has_role('admin')):
        messages.error(request, "Permission refusée. Seuls les administrateurs peuvent créer des sites.")
        return redirect('core:site_list')

    if request.method == 'POST':
        form = SiteForm(request.POST)
        if form.is_valid():
            site = form.save()
            messages.success(request, f"Site « {site.name} » créé avec succès.")
            return redirect('core:site_detail', pk=site.pk)
    else:
        form = SiteForm()

    return render(request, 'core/sites/site_form.html', {
        'form': form,
        'title': 'Nouveau site',
        'is_creation': True,
    })


@login_required
def site_edit(request, pk):
    """Modifier un site existant."""
    if not (request.user.is_admin or request.user.has_role('admin')):
        messages.error(request, "Permission refusée.")
        return redirect('core:site_list')

    site = get_object_or_404(Site, pk=pk)

    if request.method == 'POST':
        form = SiteForm(request.POST, instance=site)
        if form.is_valid():
            form.save()
            messages.success(request, f"Site « {site.name} » modifié avec succès.")
            return redirect('core:site_detail', pk=site.pk)
    else:
        form = SiteForm(instance=site)

    return render(request, 'core/sites/site_form.html', {
        'form': form,
        'site': site,
        'title': f'Modifier {site.name}',
        'is_creation': False,
    })


@login_required
def site_delete(request, pk):
    """Supprimer un site."""
    if not (request.user.is_admin or request.user.has_role('admin')):
        messages.error(request, "Permission refusée.")
        return redirect('core:site_list')

    site = get_object_or_404(Site, pk=pk)

    if site.is_main_site:
        messages.error(request, "Impossible de supprimer le site principal.")
        return redirect('core:site_detail', pk=site.pk)

    if request.method == 'POST':
        name = site.name
        site.delete()
        messages.success(request, f"Site « {name} » supprimé avec succès.")
        return redirect('core:site_list')

    from apps.members.models import Member
    member_count = Member.objects.filter(site=site).count()

    return render(request, 'core/sites/site_delete.html', {
        'site': site,
        'member_count': member_count,
    })


@login_required
def site_toggle_active(request, pk):
    """Activer/désactiver un site (HTMX)."""
    if not (request.user.is_admin or request.user.has_role('admin')):
        return JsonResponse({'success': False, 'error': 'Permission refusée'})

    site = get_object_or_404(Site, pk=pk)
    site.is_active = not site.is_active
    site.save(update_fields=['is_active'])

    status = "activé" if site.is_active else "désactivé"
    messages.success(request, f"Site « {site.name} » {status}.")

    if request.headers.get('HX-Request'):
        return JsonResponse({'success': True, 'is_active': site.is_active})
    return redirect('core:site_list')
