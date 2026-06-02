from django.urls import path
from . import driver_views


app_name = 'blog'

urlpatterns = [
    path('login/', driver_views.driver_login, name='driver_login'),
    path('logout/', driver_views.driver_logout, name='driver_logout'),
    path('', driver_views.driver_dashboard, name='driver_dashboard'),
    path('complete/<int:post_id>/', driver_views.driver_complete_trip, name='driver_complete_trip'),
    path('change-password/', driver_views.driver_change_password, name='driver_change_password'),
    path('password-change/', driver_views.driver_password_change, name='driver_password_change'),
    path('impersonate/<int:driver_id>/', driver_views.driver_impersonate, name='driver_impersonate'),
    path('impersonate/exit/', driver_views.driver_impersonate_exit, name='driver_impersonate_exit'),
    path('settlements/', driver_views.driver_settlement_list, name='driver_settlement_list'),
    path('settlements/<str:settlement_number>/', driver_views.driver_settlement_detail, name='driver_settlement_detail'),
    path('settlements/<str:settlement_number>/pdf/', driver_views.driver_settlement_pdf, name='driver_settlement_pdf'),
]

