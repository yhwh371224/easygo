import os
import logging

from twilio.rest import Client
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from blog.models import Post
from decouple import config


# Configure logging for this script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sms_logger = logging.getLogger('sms')

twilio_logger = logging.getLogger('twilio')
twilio_logger.setLevel(logging.WARNING)


class Command(BaseCommand):
    help = 'Send final notices via WhatsApp or SMS'

    def handle(self, *args, **options):
        try: 
            today = date.today()
            # tomorrow = today + timedelta(days=1)
            day_after_tomorrow = today + timedelta(days=2)
            final_notices = Post.objects.filter(pickup_date__range=[today, day_after_tomorrow])
            
            # Initialize Twilio client once
            account_sid = config('TWILIO_ACCOUNT_SID')
            auth_token = config('TWILIO_AUTH_TOKEN')
            client = Client(account_sid, auth_token)

            def format_phone_number(phone_number):
                if phone_number.startswith('+'):
                    return phone_number
                elif phone_number.startswith('0'):
                    return '+61' + phone_number[1:]
                else:
                    return '+' + phone_number

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
                    sms_logger.info(f'WhatsApp: {formatted_number}')
                except Exception as e:
                    sms_logger.error(f'Failed to send WhatsApp message to {formatted_number}: {e}')            

            def send_sms_message(sendto):
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
                    sms_logger.info(f'SMS: {formatted_number}')
                except Exception as e:
                    sms_logger.error(f'Failed to send SMS message to {formatted_number}: {e}')            

            def should_send_notice(final_notice):
                return (                     
                    not final_notice.cancelled and 
                    not final_notice.paid and 
                    not final_notice.cash
                )

            for final_notice in final_notices:
                if should_send_notice(final_notice):
                    send_sms_message(final_notice.contact)
                    if final_notice.direction == 'Pickup from Intl Airport':                
                        send_whatsapp_message(final_notice.contact)                
                    
            self.stdout.write(self.style.SUCCESS('Twilio sent final notice successfully'))
            
        except Exception as e:
            sms_logger.error(f'Error in handle method: {e}')
            self.stdout.write(self.style.ERROR('Failed to send  twilio final notices'))
