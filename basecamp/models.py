from django.db import models
from django.apps import AppConfig
from django.urls import reverse
import datetime


class Inquiry_point(models.Model):
    name = models.CharField(max_length=100, blank=False)
    company_name = models.CharField(max_length=100, blank=True)
    contact = models.CharField(max_length=50, blank=False)
    email = models.EmailField(blank=False)
    email1 = models.EmailField(blank=True)
    flight_date = models.DateField(verbose_name='flight_date', blank=False)
    flight_number = models.CharField(max_length=100, blank=True, null=True)
    flight_time = models.CharField(max_length=60, blank=True, null=True)
    pickup_time = models.CharField(max_length=30, blank=True, null=True)
    direction = models.CharField(max_length=100, blank=True, null=True)
    suburb = models.CharField(max_length=100, blank=True, null=True)
    street = models.CharField(max_length=200, blank=True, null=True)
    no_of_passenger = models.CharField(max_length=30, blank=False)
    no_of_baggage = models.CharField(max_length=200, blank=True)
    return_direction = models.CharField(max_length=100, blank=True, null=True)
    return_flight_date = models.DateField(blank=True, null=True, default=datetime.date.today)
    return_flight_number = models.CharField(max_length=200, blank=True, null=True)
    return_flight_time = models.CharField(max_length=30, blank=True, null=True)
    return_pickup_time = models.CharField(max_length=30, blank=True, null=True)
    message = models.TextField(blank=True)
    notice = models.TextField(blank=True)    
    price = models.CharField(max_length=30, blank=True)    
    paid = models.CharField(max_length=30, blank=True)
    driver = models.CharField(max_length=100, blank=True, null=True)
    is_confirmed = models.BooleanField(default=False, blank=True) 
    cancelled = models.BooleanField(default=False, blank=True) 
    private_ride = models.BooleanField(default=False, blank=True) 
    cruise = models.BooleanField(default=False, blank=True)   
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']    

        

class BasecampAppConfig(AppConfig):
    name = 'basecamp'

    def ready(self):
        from blog import signals
