from django.urls import path
from . import views


urlpatterns = [
    path('', views.sequence_form, name='sequence_form'),
    path('result/', views.sequence_result, name='sequence_result'),
]