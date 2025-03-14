# newsroom/urls.py
from django.urls import path
from . import views

app_name = 'newsroom'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Stories
    path('stories/', views.story_list, name='story_list'),
    path('stories/create/', views.story_create, name='story_create'),
    path('stories/<uuid:story_id>/', views.story_detail, name='story_detail'),
    path('stories/<uuid:story_id>/edit/', views.story_edit, name='story_edit'),
    path('stories/<uuid:story_id>/publish/', views.story_publish, name='story_publish'),
    path('stories/<uuid:story_id>/download/', views.story_download, name='story_download'),
    
    # Audio clips
    path('stories/<uuid:story_id>/audio/upload/', views.story_audio_upload, name='story_audio_upload'),
    path('stories/<uuid:story_id>/audio/<uuid:audio_id>/delete/', views.story_audio_delete, name='story_audio_delete'),
    
    # Story revisions
    path('stories/<uuid:story_id>/revisions/<uuid:revision_id>/', views.story_view_revision, name='story_revision'),
    path('stories/<uuid:story_id>/revisions/<uuid:revision_id>/restore/', views.story_restore_revision, name='story_restore_revision'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<uuid:category_id>/edit/', views.category_edit, name='category_edit'),
    path('categories/<uuid:category_id>/delete/', views.category_delete, name='category_delete'),
    
    # Tasks
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/<uuid:task_id>/', views.task_detail, name='task_detail'),
    path('tasks/<uuid:task_id>/edit/', views.task_edit, name='task_edit'),
    path('tasks/<uuid:task_id>/status-update/', views.task_status_update, name='task_status_update'),
    path('tasks/<uuid:task_id>/comment/', views.task_add_comment, name='task_add_comment'),
    path('tasks/<uuid:task_id>/attachment/', views.task_add_attachment, name='task_add_attachment'),
    path('tasks/<uuid:task_id>/attachment/<uuid:attachment_id>/delete/', views.task_delete_attachment, name='task_delete_attachment'),
]