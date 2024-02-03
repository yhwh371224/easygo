import csv
from blog.models import Inquiry, Post, Payment, Driver
from django.core.management.base import BaseCommand
from datetime import datetime

class Command(BaseCommand):
    help = 'Exports data to CSV files'

    def handle(self, *args, **kwargs):
        # Inquiry
        with open('inquiry_data.csv', 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([f.name for f in Inquiry._meta.fields])  
            for obj in Inquiry.objects.all():
                writer.writerow([getattr(obj, f.name) for f in Inquiry._meta.fields])


        # Post 
        with open('post_data.csv', 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([f.name for f in Post._meta.fields])  
            for obj in Post.objects.all():
                writer.writerow([getattr(obj, f.name) for f in Post._meta.fields])

        # Payment 
        with open('payment_data.csv', 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([f.name for f in Payment._meta.fields])  
            for obj in Payment.objects.all():
                writer.writerow([getattr(obj, f.name) for f in Payment._meta.fields])

        # Driver 
        with open('driver_data.csv', 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([f.name for f in Driver._meta.fields])  
            for obj in Driver.objects.all():
                writer.writerow([getattr(obj, f.name) for f in Driver._meta.fields])







