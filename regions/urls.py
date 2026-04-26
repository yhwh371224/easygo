from django.urls import path
from . import views

app_name = 'regions'

urlpatterns = [
    # Coming soon regions must match before the generic home route.
    path('brisbane/', views.region_coming_soon, {'region_slug': 'brisbane'}, name='coming_soon_brisbane'),
    path('perth/', views.region_coming_soon, {'region_slug': 'perth'}, name='coming_soon_perth'),
    path('adelaide/', views.region_coming_soon, {'region_slug': 'adelaide'}, name='coming_soon_adelaide'),
    path('gold-coast/', views.region_coming_soon, {'region_slug': 'gold-coast'}, name='coming_soon_gold_coast'),

    path('<slug:region_slug>/', views.region_home, name='home'),
    path('<slug:region_slug>/inquiry/', views.region_inquiry, name='inquiry'),
    path('<slug:region_slug>/inquiry_detail/', views.region_inquiry_details, name='inquiry_details'),
    path('<slug:region_slug>/booking/', views.region_booking, name='booking'),
    path('<slug:region_slug>/booking_detail/', views.region_booking_detail, name='booking_detail'),
    path('<slug:region_slug>/confirmation/', views.region_confirmation, name='confirmation'),
    path('<slug:region_slug>/meeting-point/', views.region_meeting_point, name='meeting_point'),
    path('<slug:region_slug>/arrival-guide/', views.region_arrival_guide, name='arrival_guide'),
    path('<slug:region_slug>/airport-shuttle/', views.region_airport_shuttle_list, name='airport_shuttle_list'),
    path('<slug:region_slug>/airport-shuttle/<slug:suburb_slug>/', views.airport_shuttle_suburb, name='airport_shuttle_suburb'),
]
