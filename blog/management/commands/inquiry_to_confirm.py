import os
import logging
import threading
from django.core.management.base import BaseCommand
from blog.models import Post, Inquiry, Driver
from basecamp.models import Inquiry_point
from schedule import fetch_scheduled_emails 

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger('blog.inquiry_to_confirm')
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s:%(message)s')

# Create the logs directory if it doesn't exist
logs_dir = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

file_handler = logging.FileHandler(os.path.join(logs_dir, 'inquiry_to_confirm.log'))
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)


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

                user = (Inquiry.objects.filter(email=list_email).first()) or (Inquiry_point.objects.filter(email=list_email).first())

                sam_driver = Driver.objects.get(driver_name="Sam")    
        
                p = Post(name=user.name, contact=user.contact, email=user.email, company_name=user.company_name, email1=user.email1, flight_date=user.flight_date, 
                flight_number=user.flight_number, flight_time=user.flight_time, pickup_time=user.pickup_time, direction=user.direction, suburb=user.suburb, street=user.street, 
                no_of_passenger=user.no_of_passenger, no_of_baggage=user.no_of_baggage, return_direction=user.return_direction, return_flight_date=user.return_flight_date, 
                return_flight_number=user.return_flight_number, return_flight_time=user.return_flight_time, return_pickup_time=user.return_pickup_time, message=user.message, 
                notice=user.notice, price=user.price, paid=user.paid, is_confirmed=user.is_confirmed, driver=sam_driver)

                p.save()

                logger.info(f'....{user.name}, {user.flight_date}, {user.pickup_time} | {user.return_flight_date}, {user.return_flight_number}')