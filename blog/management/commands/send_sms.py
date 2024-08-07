import os
import logging

from twilio.rest import Client
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from blog.models import Post
from decouple import config

# Configure logging for this script
LOGGING_DIR = os.path.join(os.path.dirname(__file__), 'logs')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s %(asctime)s %(module)s %(message)s',
    handlers=[logging.FileHandler(os.path.join(LOGGING_DIR, 'sms.log'))]
)

sms_logger = logging.getLogger()


class Command(BaseCommand):
    help = 'Send final notices via WhatsApp or SMS'

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

        def send_whatsapp_message(sendto):
            formatted_number = format_phone_number(sendto)
            try:
                message = client.messages.create(
                    body="EasyGo - Urgent notice \
                        \n\nWe haven't received your payment and a response to our emails. \
                        \nPlease email us ASAP to ensure your booking remains confirmed \
                        \nReply only via email >> info@easygoshuttle.com.au",
                    from_='whatsapp:+14155238886',  # Your Twilio WhatsApp-enabled number
                    to=f'whatsapp:{formatted_number}'
                )
                sms_logger.info(f'WhatsApp message sent to {formatted_number}')
            except Exception as e:
                sms_logger.error(f'Failed to send WhatsApp message to {formatted_number}: {e}')            

        def send_sms_message(sendto, message_body):
            formatted_number = format_phone_number(sendto)
            try:
                message = client.messages.create(
                    body="EasyGo - Urgent notice \
                          \n\nWe haven't received your payment and a response to our emails. \
                          \nPlease email us ASAP to ensure your booking remains confirmed \
                          \nReply only via email >> info@easygoshuttle.com.au",
                    from_='+18148920523',  # Your Twilio SMS number
                    to=formatted_number
                )
                sms_logger.info(f'SMS message sent to {formatted_number}')
            except Exception as e:
                sms_logger.error(f'Failed to send SMS message to {formatted_number}: {e}')
            

        sent_numbers = []  
        for final_notice in final_notices:
            if not final_notice.reminder and not final_notice.cancelled and not final_notice.paid:                
                send_sms_message(final_notice.contact) 
                send_whatsapp_message(final_notice.contact)
                
                if final_notice.contact:
                    sent_numbers.append(final_notice.contact)  

        # Prepare log message to be sent to office numbers
        log_message = "\n".join([f'Twilio sent message to {number}' for number in sent_numbers])
        sms_logger.info(log_message)

        self.stdout.write(self.style.SUCCESS('Twilio sent final notice successfully'))
