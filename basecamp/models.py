from django.db import models
from django.apps import AppConfig


class Point(models.Model):
    name = models.CharField(max_length=100, blank=False)
    contact = models.CharField(max_length=50, blank=False)
    email = models.EmailField(blank=False)

    date = models.DateField(verbose_name='date', blank=False)    
    pickuptime = models.CharField(max_length=30, blank=True)

    startpoint = models.CharField(max_length=200, blank=False)
    endpoint = models.CharField(max_length=200, blank=False)
    
    passenger = models.CharField(max_length=30, blank=False)
    baggage = models.CharField(max_length=200, blank=True)
    message = models.TextField(blank=True)

    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']
    
    def get_absolute_url(self):
        return '/basecamp/point{}/'.format(self.pk)
    
    
