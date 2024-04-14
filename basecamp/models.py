# from django.db import models
# from django.apps import AppConfig
# from django.urls import reverse
# import datetime


# class Booking_p2p(models.Model):
#     company_name = models.CharField(max_length=100, blank=True)
#     email1 = models.EmailField(blank=True)
#     p2p_name = models.CharField(max_length=100)
#     p2p_phone = models.CharField(max_length=20)
#     p2p_email = models.EmailField()
#     p2p_date = models.DateField()
#     first_pickup_location = models.CharField(max_length=200)
#     first_putime = models.CharField(max_length=30, blank=True, null=True)
#     first_dropoff_location = models.CharField(max_length=200)
#     second_pickup_location = models.CharField(max_length=200, blank=True, null=True)
#     second_putime = models.CharField(max_length=30, blank=True, null=True)
#     second_dropoff_location = models.CharField(max_length=200, blank=True, null=True)
#     third_pickup_location = models.CharField(max_length=200, blank=True, null=True)
#     third_putime = models.CharField(max_length=30, blank=True, null=True)
#     third_dropoff_location = models.CharField(max_length=200, blank=True, null=True)
#     fourth_pickup_location = models.CharField(max_length=200, blank=True, null=True)
#     fourth_putime = models.CharField(max_length=30, blank=True, null=True)
#     fourth_dropoff_location = models.CharField(max_length=200, blank=True, null=True)
#     p2p_passengers = models.CharField(max_length=30, blank=False)
#     p2p_baggage = models.CharField(max_length=200, blank=True)
#     p2p_message = models.TextField(blank=True)
#     notice = models.CharField(max_length=200, blank=True, null=True)    
#     price = models.CharField(max_length=30, blank=True)    
#     paid = models.CharField(max_length=30, blank=True)
#     is_confirmed = models.BooleanField(default=False, blank=True) 
#     cancelled = models.BooleanField(default=False, blank=True)  
#     created = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         ordering = ['-created']    


# class Inquiry_cruise(models.Model):
#     name = models.CharField(max_length=100, blank=False)
#     company_name = models.CharField(max_length=100, blank=True)
#     contact = models.CharField(max_length=50, blank=False)
#     email = models.EmailField(blank=False, db_index=True)
#     email1 = models.EmailField(blank=True)
#     flight_date = models.DateField(verbose_name='flight_date', blank=False)
#     flight_number = models.CharField(max_length=100, blank=True, null=True)
#     flight_time = models.CharField(max_length=60, blank=True, null=True)
#     pickup_time = models.CharField(max_length=30, blank=True, null=True)
#     direction = models.CharField(max_length=100, blank=True, null=True)
#     suburb = models.CharField(max_length=100, blank=True, null=True)
#     Second_location = models.CharField(max_length=200, blank=True, null=True)
#     no_of_passenger = models.CharField(max_length=30, blank=False)
#     no_of_baggage = models.CharField(max_length=200, blank=True)
#     return_direction = models.CharField(max_length=100, blank=True, null=True)
#     return_flight_date = models.DateField(blank=True, null=True, default=datetime.date.today)
#     return_flight_number = models.CharField(max_length=200, blank=True, null=True)
#     return_flight_time = models.CharField(max_length=30, blank=True, null=True)
#     return_pickup_time = models.CharField(max_length=30, blank=True, null=True)
#     message = models.TextField(blank=True)
#     notice = models.TextField(blank=True)    
#     price = models.CharField(max_length=30, blank=True)    
#     paid = models.CharField(max_length=30, blank=True)
#     # driver = models.CharField(max_length=100, blank=True, null=True)
#     driver = models.ForeignKey('Driver', on_delete=models.CASCADE, null=True, blank=True)
#     meeting_point = models.CharField(max_length=100, blank=True, null=True)
#     is_confirmed = models.BooleanField(default=False, blank=True) 
#     cancelled = models.BooleanField(default=False, blank=True) 
#     private_ride = models.BooleanField(default=False, blank=True) 
#     cruise = models.BooleanField(default=False, blank=True)   
#     created = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         ordering = ['-created']   
        

# class BasecampAppConfig(AppConfig):
#     name = 'basecamp'

#     def ready(self):
#         from blog import signals
