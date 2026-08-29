"""Authorization boundary for bulk exports.

Exports are mass-disclosure operations and intentionally require stronger
permissions than an ordinary authenticated page view.
"""
from django.contrib.auth.decorators import login_required

from apps.core.permissions import role_required
from . import views as legacy_views


@login_required
@role_required('admin', 'secretariat')
def export_members(request):
    return legacy_views.export_members(request)


@login_required
@role_required('admin', 'secretariat')
def export_children(request):
    return legacy_views.export_children(request)


@login_required
@role_required('admin', 'secretariat')
def export_young_members(request):
    return legacy_views.export_young_members(request)


@login_required
@role_required('admin', 'secretariat')
def export_groups(request):
    return legacy_views.export_groups(request)


@login_required
@role_required('admin')
def export_inventory(request):
    return legacy_views.export_inventory(request)


@login_required
@role_required('admin')
def export_transport(request):
    return legacy_views.export_transport(request)


@login_required
@role_required('admin', 'secretariat')
def export_communication(request):
    return legacy_views.export_communication(request)
