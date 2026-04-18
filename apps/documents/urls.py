from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('', views.document_list, name='list'),
    path('upload/', views.document_upload, name='upload'),
    path('categories/', views.category_list, name='categories'),
    path('stats/', views.document_stats, name='stats'),
    path('shared/<uuid:token>/', views.shared_access, name='shared_access'),
    path('<int:pk>/', views.document_detail, name='detail'),
    path('<int:pk>/download/', views.document_download, name='download'),
    path('<int:pk>/stream/', views.document_stream, name='stream'),
    path('<int:pk>/preview/', views.document_preview, name='preview'),
    path('<int:pk>/edit/', views.document_edit, name='edit'),
    path('<int:pk>/delete/', views.document_delete, name='delete'),
    path('<int:pk>/share/', views.document_share, name='share'),
]
