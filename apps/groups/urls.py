from django.urls import path
from . import views

app_name = 'groups'

urlpatterns = [
    path('', views.group_list, name='list'),
    path('dashboard/', views.groups_dashboard, name='dashboard'),
    path('create/', views.group_create, name='create'),
    path('<int:pk>/', views.group_detail, name='detail'),
    path('<int:pk>/edit/', views.group_update, name='update'),
    path('<int:pk>/delete/', views.group_delete, name='delete'),
    path('<int:pk>/members/', views.group_members_manage, name='members_manage'),
    path('<int:pk>/statistics/', views.group_statistics, name='statistics'),
    path('<int:pk>/generate-meetings/', views.group_generate_meetings, name='generate_meetings'),
    path('<int:group_pk>/meetings/create/', views.group_meeting_create, name='meeting_create'),
    path('<int:group_pk>/meetings/<int:meeting_pk>/edit/', views.group_meeting_update, name='meeting_update'),
    path('<int:group_pk>/meetings/<int:meeting_pk>/delete/', views.meeting_delete, name='meeting_delete'),
]

