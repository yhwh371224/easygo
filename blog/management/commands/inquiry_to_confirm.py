import os
import threading
from django.core.management.base import BaseCommand
from blog.models import Post, Inquiry, Driver
from schedule import fetch_scheduled_emails 


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Command(BaseCommand):
    help = 'To confirm the inquiries for booking'

    def __init__(self):
        self.lock = threading.Lock()

    def handle(self, *args, **options):
        my_list = fetch_scheduled_emails() 
        unique_emails = set() 
        
        with self.lock:
            for list_email in my_list:

                if list_email in unique_emails:                    
                    continue

                else: 
                    unique_emails.add(list_email)

                    user = (Inquiry.objects.filter(email=list_email).first()) 
    
                    sam_driver = Driver.objects.get(driver_name="Sam")    
            
                    p = Post(name=user.name, contact=user.contact, email=user.email, company_name=user.company_name, email1=user.email1, pickup_date=user.pickup_date, 
                    flight_number=user.flight_number, flight_time=user.flight_time, pickup_time=user.pickup_time, direction=user.direction, suburb=user.suburb, street=user.street, 
                    no_of_passenger=user.no_of_passenger, no_of_baggage=user.no_of_baggage, return_direction=user.return_direction, return_pickup_date=user.return_pickup_date, 
                    return_flight_number=user.return_flight_number, return_flight_time=user.return_flight_time, return_pickup_time=user.return_pickup_time, message=user.message, 
                    notice=user.notice, price=user.price, paid=user.paid, is_confirmed=user.is_confirmed, driver=sam_driver)
    
                    p.save()
    