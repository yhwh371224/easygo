from django.urls import path
from . import views
from django.views.generic import RedirectView
from regions.views.wrappers import make_region_view
from basecamp.views.misc_inquirys import price_detail
from basecamp.views.inquirys import inquiry_details1


app_name = 'regions'

urlpatterns = [
    # Region pillar pages
    path('<slug:region_slug>/airport-shuttle/', views.region_airport_shuttle, name='region_airport_shuttle'),
    path('<slug:region_slug>/airport-transfer/', views.region_airport_transfer, name='region_airport_transfer'),
    path('<slug:region_slug>/cruise-transfer/', views.region_cruise_transfer, name='region_cruise_transfer'),
    path('<slug:region_slug>/maxi-taxi/', views.region_maxi_taxi, name='region_maxi_taxi'),

    path('sydney/', RedirectView.as_view(url='/', permanent=False)),

    path('<slug:region_slug>/', views.region_home, name='home'),

    # Legacy basecamp flows made region-aware
    path('<slug:region_slug>/price_detail/', make_region_view(price_detail), name='price_detail'),
    path('<slug:region_slug>/inquiry_details1/', make_region_view(inquiry_details1), name='inquiry_details1'),
    path('<slug:region_slug>/inquiry/', views.region_inquiry, name='inquiry'),
    path('<slug:region_slug>/inquiry_detail/', views.region_inquiry_details, name='inquiry_details'),
    path('<slug:region_slug>/booking/', views.region_booking, name='booking'),
    path('<slug:region_slug>/booking_detail/', views.region_booking_detail, name='booking_detail'),
    path('<slug:region_slug>/confirmation/', views.region_confirmation, name='confirmation'),
    path('<slug:region_slug>/meeting-point/', views.region_meeting_point, name='region_meeting_point'),
    path('<slug:region_slug>/arrival-guide/', views.region_arrival_guide, name='arrival_guide'),
    path('<slug:region_slug>/airport-shuttle/<slug:suburb_slug>/', views.airport_shuttle_suburb, name='airport_shuttle_suburb'),
    path('<slug:region_slug>-airport-transfer/<slug:suburb_slug>/', views.airport_shuttle_suburb, name='airport_transfer_suburb'),

    # path('<slug:region_slug>/inquiry_done/', views.region_inquiry_done, name='inquiry_done'),
]