from django.contrib.auth.decorators import login_required
from django.urls import path

from apps.core.permissions import role_required
from . import views
from .role_router import role_home

app_name = 'dashboard'


def admin_access(view):
    """Applique l'authentification avant le contrôle RBAC admin."""
    return login_required(role_required('admin')(view))


urlpatterns = [
    path('', role_home, name='home'),
    path('stats/', admin_access(views.quick_stats), name='stats'),
    path('search/', admin_access(views.global_search), name='search'),
]
