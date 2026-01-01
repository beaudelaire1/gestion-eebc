"""URLs pour le module Finance."""

from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/create/', views.transaction_create, name='transaction_create'),
    path('transactions/<int:pk>/', views.transaction_detail, name='transaction_detail'),
    path('transactions/<int:pk>/validate/', views.transaction_validate, name='transaction_validate'),
    path('proofs/<int:pk>/upload/', views.proof_upload, name='proof_upload'),
    path('budget/', views.budget_overview, name='budget_overview'),
    path('reports/', views.reports, name='reports'),
]
