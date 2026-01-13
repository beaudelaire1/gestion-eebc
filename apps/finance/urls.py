"""URLs pour le module Finance."""

from django.urls import path
from . import views
from . import budget_views

app_name = 'finance'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/chart-data/', views.dashboard_chart_data, name='dashboard_chart_data'),
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
    
    # Système de budget
    path('budgets/', budget_views.budget_dashboard, name='budget_dashboard'),
    path('budgets/list/', budget_views.budget_list, name='budget_list'),
    path('budgets/create/', budget_views.budget_create, name='budget_create'),
    path('budgets/<int:budget_id>/', budget_views.budget_detail, name='budget_detail'),
    path('budgets/<int:budget_id>/approve-detailed/', budget_views.budget_approve_detailed, name='budget_approve_detailed'),
    path('budgets/<int:budget_id>/submit/', budget_views.budget_submit, name='budget_submit'),
    path('budgets/<int:budget_id>/edit/', budget_views.budget_edit, name='budget_edit'),
    
    # Catégories de budget
    path('budget-categories/', views.budget_category_list, name='budget_category_list'),
    path('budget-categories/create/', views.budget_category_create, name='budget_category_create'),
    path('budget-categories/<int:pk>/edit/', views.budget_category_update, name='budget_category_update'),
    path('budget-categories/<int:pk>/delete/', views.budget_category_delete, name='budget_category_delete'),
    
    # Export et impression des budgets
    path('budgets/<int:budget_id>/export-excel/', budget_views.budget_export_excel, name='budget_export_excel'),
    path('budgets/<int:budget_id>/print/', budget_views.budget_print_view, name='budget_print'),
    path('budgets/export-list/', budget_views.budget_list_export_excel, name='budget_list_export_excel'),
    
    # Export des transactions
    path('transactions/export-excel/', budget_views.transactions_export_excel, name='transactions_export_excel'),
    
    # Demandes de budget
    path('budget-requests/', budget_views.budget_request_list, name='budget_request_list'),
    path('budget-requests/create/', budget_views.budget_request_create, name='budget_request_create'),
    path('budget-requests/<int:request_id>/', budget_views.budget_request_detail, name='budget_request_detail'),
    
    # Justificatifs avec OCR
    path('receipts/', views.receipt_proof_list, name='receipt_proof_list'),
    path('receipts/upload/', views.receipt_proof_upload, name='receipt_proof_upload'),
    path('receipts/<int:pk>/process-ocr/', views.receipt_process_ocr, name='receipt_process_ocr'),
    path('receipts/batch-retry-ocr/', views.batch_retry_ocr, name='batch_retry_ocr'),
    
    # API endpoints pour OCR
    path('api/receipts/<int:pk>/ocr-status/', views.receipt_ocr_status_api, name='receipt_ocr_status_api'),
    path('api/receipts/batch-ocr-status/', views.batch_ocr_status_api, name='batch_ocr_status_api'),
]
