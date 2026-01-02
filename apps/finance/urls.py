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
    
    # Reçus fiscaux
    path('tax-receipts/', views.tax_receipt_list, name='tax_receipt_list'),
    path('tax-receipts/create/', views.tax_receipt_create, name='tax_receipt_create'),
    path('tax-receipts/<int:pk>/', views.tax_receipt_detail, name='tax_receipt_detail'),
    path('tax-receipts/<int:pk>/pdf/', views.tax_receipt_pdf, name='tax_receipt_pdf'),
    path('tax-receipts/<int:pk>/send/', views.tax_receipt_send, name='tax_receipt_send'),
    
    # Justificatifs avec OCR
    path('receipts/', views.receipt_proof_list, name='receipt_proof_list'),
    path('receipts/upload/', views.receipt_proof_upload, name='receipt_proof_upload'),
    path('receipts/<int:pk>/process-ocr/', views.receipt_process_ocr, name='receipt_process_ocr'),
]
