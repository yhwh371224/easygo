from django.urls import path
from . import views

urlpatterns = [
    path('', views.calculate_trade, name='calculate_trade'),
]
