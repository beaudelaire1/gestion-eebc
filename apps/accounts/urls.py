from django.urls import path
from . import views
from . import security_views as sv
from . import import_security as import_sv
from .two_factor_views import (
    TwoFactorSetupView,
    TwoFactorDisableView,
    TwoFactorBackupCodesView,
)

app_name = 'accounts'

urlpatterns = [
    # Authentification
    path('login/', sv.secure_login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('first-login-password-change/', views.first_login_password_change, name='first_login_password_change'),

    # Profil
    path('profile/', views.profile_view, name='profile'),

    # Double authentification (2FA)
    path('2fa/setup/', TwoFactorSetupView.as_view(), name='two_factor_setup'),
    path('2fa/disable/', TwoFactorDisableView.as_view(), name='two_factor_disable'),
    path('2fa/verify/', sv.SecureTwoFactorVerifyView.as_view(), name='two_factor_verify'),
    path('2fa/backup-codes/', TwoFactorBackupCodesView.as_view(), name='two_factor_backup_codes'),

    # Gestion des utilisateurs
    path('users/', views.user_list_view, name='user_list'),
    path('users/create/', sv.secure_create_user_view, name='create_user'),
    path('users/import/', import_sv.secure_user_bulk_import_view, name='user_bulk_import'),
    path('users/import/template/', views.user_bulk_import_template, name='user_bulk_import_template'),
    path('users/<int:user_id>/', views.user_detail_view, name='user_detail'),
    path('users/<int:user_id>/edit/', sv.secure_user_update_view, name='user_update'),
    path('users/<int:user_id>/delete/', sv.secure_user_delete_view, name='user_delete'),
    path('users/<int:user_id>/activate/', sv.secure_user_activate_view, name='user_activate'),

    # Actions utilisateurs
    path('resend-invitation/<int:user_id>/', sv.secure_resend_invitation, name='resend_invitation'),
    path('reset-password/<int:user_id>/', sv.secure_reset_user_password, name='reset_password'),
]
