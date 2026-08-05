from django.urls import path
from . import driver_views


app_name = 'blog_apply'

urlpatterns = [
    path('apply/', driver_views.driver_apply, name='driver_apply'),
]
