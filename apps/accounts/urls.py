from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentification
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('first-login-password-change/', views.first_login_password_change, name='first_login_password_change'),
    
    # Profil
    path('profile/', views.profile_view, name='profile'),
    
    # Gestion des utilisateurs (équipe)
    path('users/', views.user_list_view, name='user_list'),
    path('users/create/', views.create_user_view, name='create_user'),
    path('resend-invitation/<int:user_id>/', views.resend_invitation, name='resend_invitation'),
    path('reset-password/<int:user_id>/', views.reset_user_password, name='reset_password'),
]