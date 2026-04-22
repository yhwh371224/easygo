from django.urls import path
from . import views, driver_views


app_name = 'blog'

urlpatterns = [
    # path('pay/xrp/', views.xrp_payment, name='pay_xrp'),
    # path('pay/xrp/page/', views.xrp_payment_page, name='pay_xrp_page'),
    path('driver/login/', driver_views.driver_login, name='driver_login'),
    path('driver/logout/', driver_views.driver_logout, name='driver_logout'),
    path('driver/', driver_views.driver_dashboard, name='driver_dashboard'),
    path('driver/complete/<int:post_id>/', driver_views.driver_complete_trip, name='driver_complete_trip'),
]

