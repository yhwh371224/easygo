from django.urls import path
from . import views

app_name = 'regions'

urlpatterns = [
    path('<slug:region_slug>/', views.region_home, name='home'),
    path('<slug:region_slug>/booking/', views.region_booking, name='booking'),
    path('<slug:region_slug>/confirmation/', views.region_confirmation, name='confirmation'),
    path('<slug:region_slug>/airport-shuttle/<slug:suburb_slug>/', views.airport_shuttle_suburb, name='airport_shuttle_suburb'),
]
