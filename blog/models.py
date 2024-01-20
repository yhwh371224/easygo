import datetime

from django.db import models
from django.apps import AppConfig
from django.urls import reverse


class Inquiry(models.Model):
    name = models.CharField(max_length=100, blank=False)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    contact = models.CharField(max_length=50, blank=False)
    email = models.EmailField(blank=False, db_index=True)
    email1 = models.EmailField(blank=True, null=True)
    flight_date = models.DateField(verbose_name='flight_date', blank=False)
    flight_number = models.CharField(max_length=100, blank=False)
    flight_time = models.CharField(max_length=30, blank=False)
    pickup_time = models.CharField(max_length=30, blank=True, null=True)
    direction = models.CharField(max_length=100, blank=True, null=True)
    suburb = models.CharField(max_length=100, blank=False)
    street = models.CharField(max_length=200, blank=False)
    no_of_passenger = models.CharField(max_length=30, blank=False)
    no_of_baggage = models.CharField(max_length=200, blank=True, null=True)
    return_direction = models.CharField(max_length=100, blank=True, null=True)
    return_flight_date = models.DateField(blank=True, null=True, default=datetime.date.today)
    return_flight_number = models.CharField(max_length=100, blank=True, null=True)
    return_flight_time = models.CharField(max_length=30, blank=True, null=True)
    return_pickup_time = models.CharField(max_length=30, blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    notice = models.TextField(blank=True, null=True)    
    price = models.CharField(max_length=100, blank=True, null=True)    
    paid = models.CharField(max_length=30, blank=True, null=True)
    driver = models.ForeignKey('Driver', on_delete=models.CASCADE, null=True, blank=True)
    meeting_point = models.CharField(max_length=100, blank=True, null=True)
    is_confirmed = models.BooleanField(default=False, blank=True)        
    cancelled = models.BooleanField(default=False, blank=True) 
    private_ride = models.BooleanField(default=False, blank=True)    
    created = models.DateTimeField(auto_now_add=True)

    class Meta:        
        ordering = ['-created']
    
    def get_absolute_url(self):
        return '/blog/inquiry{}/'.format(self.pk)

    def get_confirm_url(self):
        return reverse('confirm_reminder', kwargs={'email': self.email})
    
        
class Post(models.Model):
    name = models.CharField(max_length=100, blank=False)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    contact = models.CharField(max_length=50, blank=False)
    email = models.EmailField(blank=False, db_index=True)
    email1 = models.EmailField(blank=True, null=True)
    flight_date = models.DateField(verbose_name='flight_date', blank=False)
    flight_number = models.CharField(max_length=100, blank=False)
    flight_time = models.CharField(max_length=30, blank=False)
    pickup_time = models.CharField(max_length=30, blank=True, null=True)
    direction = models.CharField(max_length=100, blank=True, null=True)
    suburb = models.CharField(max_length=100, blank=False)
    street = models.CharField(max_length=200, blank=False)
    no_of_passenger = models.CharField(max_length=30, blank=False)
    no_of_baggage = models.CharField(max_length=200, blank=True, null=True)
    return_direction = models.CharField(max_length=100, blank=True, null=True)
    return_flight_date = models.DateField(blank=True, null=True, default=datetime.date.today)
    return_flight_number = models.CharField(max_length=100, blank=True, null=True)
    return_flight_time = models.CharField(max_length=30, blank=True, null=True)
    return_pickup_time = models.CharField(max_length=30, blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    notice = models.TextField(blank=True, null=True)
    price = models.CharField(max_length=100, blank=True, null=True)
    paid = models.CharField(max_length=30, blank=True, null=True)
    driver = models.ForeignKey('Driver', on_delete=models.CASCADE, null=True, blank=True)
    meeting_point = models.CharField(max_length=100, blank=True, null=True)
    is_confirmed = models.BooleanField(default=False, blank=True)
    cancelled = models.BooleanField(default=False, blank=True)    
    private_ride = models.BooleanField(default=False, blank=True)
    reminder = models.BooleanField(default=False, blank=True)
    sent_email = models.BooleanField(default=False, blank=True)
    calendar_event_id = models.CharField(max_length=255, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def get_absolute_url(self):
        return '/blog/{}/'.format(self.pk)

    def get_update_url(self):
        return self.get_absolute_url() + 'update/'
    

class Payment(models.Model):
    item_name = models.CharField(max_length=100, blank=True, null=True)
    payer_email = models.EmailField(blank=True, null=True)
    gross_amount = models.CharField(max_length=30, blank=True, null=True)
    txn_id = models.CharField(max_length=30, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']


class Driver(models.Model):
    driver_name = models.CharField(max_length=100, blank=True, null=True)
    driver_contact = models.CharField(max_length=50, blank=True, null=True)
    driver_email = models.EmailField(blank=True, null=True)
    driver_address = models.CharField(max_length=200, blank=True, null=True)
    driver_plate = models.CharField(max_length=30, blank=True, null=True)
    driver_car = models.CharField(max_length=30, blank=True, null=True)
    driver_bankdetails = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.driver_name 
    

class BlogAppConfig(AppConfig):
    name = 'blog'

    def ready(self):
        from . import signals


