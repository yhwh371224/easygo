from django.urls import path
from . import views


urlpatterns = [
    path('', views.lotto_form, name='lotto_form'),
    path('result/', views.lotto_result, name='lotto_result'),
]