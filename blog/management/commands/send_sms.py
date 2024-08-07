import os
from twilio.rest import Client
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from blog.models import Post
from decouple import config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Command(BaseCommand):
    help = 'Send final notices'

    def handle(self, *args, **options):
        tomorrow = date.today() + timedelta(days=1)
        final_notices = Post.objects.filter(pickup_date=tomorrow)
        
        # Initialize Twilio client once
        account_sid = config('TWILIO_ACCOUNT_SID')
        auth_token = config('TWILIO_AUTH_TOKEN')
        client = Client(account_sid, auth_token)

        def format_phone_number(phone_number):
            if not phone_number.startswith('+'):
                phone_number = '+61' + phone_number.lstrip('0')
            return phone_number

        def sms_one(sendto):
            formatted_number = format_phone_number(sendto)
            client.messages.create(
                body="EasyGo - Urgent notice \
                      \n\nWe haven't received your payment and a response to our emails. \
                      \nPlease contact us ASAP or your booking may be canceled. \
                      \nReply only via email >> info@easygoshuttle.com.au",
                from_='+18148920523',
                to=formatted_number
            )

        for final_notice in final_notices:
            if not final_notice.reminder and not final_notice.cancelled and not final_notice.paid:
                sms_contact = final_notice.contact  
                if sms_contact:
                    sms_one(sms_contact)

        self.stdout.write(self.style.SUCCESS('Successfully sent final notices via SMS'))
