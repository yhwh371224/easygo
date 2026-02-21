from django.urls import path
from . import views


app_name = 'blog'

urlpatterns = [
    path('pay/xrp/', views.xrp_payment, name='pay_xrp'),
    path('pay/xrp/page/', views.xrp_payment_page, name='pay_xrp_page'), 
]

