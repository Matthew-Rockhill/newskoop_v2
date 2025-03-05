from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    # Station management
    path('stations/', views.station_list, name='station_list'),
    path('stations/create/', views.station_create, name='station_create'),
    path('stations/<uuid:station_id>/', views.station_detail, name='station_detail'),
    path('stations/<uuid:station_id>/edit/', views.station_edit, name='station_edit'),
    path('stations/<uuid:station_id>/delete/', views.station_delete, name='station_delete_confirm'),

    # User management
    path('users/', views.user_list, name='user_list'),
    path('users/create/staff/', views.create_staff_user, name='create_staff_user'),
    path('users/create/radio/', views.create_radio_user, name='create_radio_user'),
    path('users/<uuid:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<uuid:user_id>/delete/', views.delete_user, name='delete_user_confirm'),
    path('users/<uuid:user_id>/reset-password/', views.reset_password, name='reset_password'),
]
