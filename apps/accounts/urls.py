from django.urls import path
from . import views
from . import two_factor_views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('profile/', views.profile_view, name='profile'),
    
    # Double authentification (2FA)
    path('2fa/setup/', two_factor_views.TwoFactorSetupView.as_view(), name='two_factor_setup'),
    path('2fa/verify/', two_factor_views.TwoFactorVerifyView.as_view(), name='two_factor_verify'),
    path('2fa/disable/', two_factor_views.TwoFactorDisableView.as_view(), name='two_factor_disable'),
    path('2fa/backup-codes/', two_factor_views.TwoFactorBackupCodesView.as_view(), name='two_factor_backup_codes'),
]

