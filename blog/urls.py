from django.urls import path
from . import driver_views


app_name = 'blog'

urlpatterns = [
    path('driver/login/', driver_views.driver_login, name='driver_login'),
    path('driver/logout/', driver_views.driver_logout, name='driver_logout'),
    path('driver/', driver_views.driver_dashboard, name='driver_dashboard'),
    path('driver/complete/<int:post_id>/', driver_views.driver_complete_trip, name='driver_complete_trip'),
    path('driver/change-password/', driver_views.driver_change_password, name='driver_change_password'),
    path('driver/password-change/', driver_views.driver_password_change, name='driver_password_change'),
    path('driver/impersonate/<int:driver_id>/', driver_views.driver_impersonate, name='driver_impersonate'),
    path('driver/impersonate/exit/', driver_views.driver_impersonate_exit, name='driver_impersonate_exit'),
]

