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
    
    # Gestion des utilisateurs (équipe) - CRUD complet
    path('users/', views.user_list_view, name='user_list'),
    path('users/create/', views.create_user_view, name='create_user'),
    path('users/<int:user_id>/', views.user_detail_view, name='user_detail'),
    path('users/<int:user_id>/edit/', views.user_update_view, name='user_update'),
    path('users/<int:user_id>/delete/', views.user_delete_view, name='user_delete'),
    path('users/<int:user_id>/activate/', views.user_activate_view, name='user_activate'),
    
    # Actions utilisateurs
    path('resend-invitation/<int:user_id>/', views.resend_invitation, name='resend_invitation'),
    path('reset-password/<int:user_id>/', views.reset_user_password, name='reset_password'),
]