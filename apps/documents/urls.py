from django.urls import path
from . import views
from . import generation_views as gv

app_name = 'documents'

urlpatterns = [
    path('', views.document_list, name='list'),
    path('upload/', views.document_upload, name='upload'),
    path('categories/', views.category_list, name='categories'),
    path('stats/', views.document_stats, name='stats'),
    path('shared/<uuid:token>/', views.shared_access, name='shared_access'),

    # Éditeur de documents générés
    path('generated/', gv.generated_list, name='generated_list'),
    path('generated/new/', gv.generated_create, name='generated_create'),
    path('generated/templates/', gv.generated_template_snippet, name='generated_template'),
    path('generated/<int:pk>/edit/', gv.generated_edit, name='generated_edit'),
    path('generated/<int:pk>/preview/', gv.generated_preview, name='generated_preview'),
    path('generated/<int:pk>/pdf/', gv.generated_pdf, name='generated_pdf'),
    path('generated/<int:pk>/finalize/', gv.generated_finalize, name='generated_finalize'),
    path('generated/<int:pk>/delete/', gv.generated_delete, name='generated_delete'),

    path('<int:pk>/', views.document_detail, name='detail'),
    path('<int:pk>/download/', views.document_download, name='download'),
    path('<int:pk>/stream/', views.document_stream, name='stream'),
    path('<int:pk>/preview/', views.document_preview, name='preview'),
    path('<int:pk>/edit/', views.document_edit, name='edit'),
    path('<int:pk>/delete/', views.document_delete, name='delete'),
    path('<int:pk>/share/', views.document_share, name='share'),
]
