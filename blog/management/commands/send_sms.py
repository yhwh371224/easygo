import os
import logging

from twilio.rest import Client
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from blog.models import Post
from decouple import config
from django.db.models import Q


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
            day_after_tomorrow = today + timedelta(days=3)
            final_notices = Post.objects.filter(
                    pickup_date__range=[today, day_after_tomorrow],
                    cancelled=False,
                    reminder=False,
                ).filter(
                    Q(paid__isnull=True) | Q(paid__exact="")
                )
            
            # Initialize Twilio client once
            account_sid = config('TWILIO_ACCOUNT_SID')
            auth_token = config('TWILIO_AUTH_TOKEN')
            sms_from = config('TWILIO_SMS_FROM')
            whatsapp_from = config('TWILIO_WHATSAPP_FROM')
            client = Client(account_sid, auth_token)

            def format_phone_number(phone_number):
                if not phone_number:
                    return None
                phone_number = phone_number.strip()
                if phone_number.startswith('+'):
                    return phone_number
                elif phone_number.startswith('0'):
                    return '+61' + phone_number[1:]
                else:
                    return '+' + phone_number

            def send_whatsapp_message(sendto, name, email, price):
                formatted_number = format_phone_number(sendto)
                try:
                    message = client.messages.create(
                        body="EasyGo - Urgent notice \
                            \n\nWe haven't received your response to our emails. \
                            \nPlease email us ASAP to ensure your booking remains confirmed \
                            \nReply only via email >> info@easygoshuttle.com.au",
                        from_=whatsapp_from,
                        to=f'whatsapp:{formatted_number}'
                    )
                    sms_logger.info(f"WhatsApp sent to {name} ({email}) at {formatted_number} | Price: ${price}")
                except Exception as e:
                    sms_logger.error(f"Failed to send WhatsApp to {name} ({email}) at {formatted_number} | Price: ${price} | Error: {e}")
            

            def send_sms_message(sendto, name, email, price):
                formatted_number = format_phone_number(sendto)
                try:
                    message = client.messages.create(
                        body="EasyGo - Urgent notice \
                            \n\nWe haven't received your payment and a response to our emails. \
                            \nPlease email us ASAP to ensure your booking remains confirmed \
                            \nReply only via email >> info@easygoshuttle.com.au",
                        from_=sms_from,
                        to=formatted_number
                    )
                    sms_logger.info(f"SMS sent to {name} ({email}) at {formatted_number} | Price: ${price}")
                except Exception as e:
                    sms_logger.error(f"Failed to send SMS to {name} ({email}) at {formatted_number} | Price: ${price} | Error: {e}")            

            def should_send_notice(final_notice):
                return not final_notice.cash

            for final_notice in final_notices:
                if should_send_notice(final_notice) and final_notice.contact:
                    send_sms_message(final_notice.contact, final_notice.name, final_notice.email, final_notice.price)
                    if final_notice.direction == 'Pickup from Intl Airport':
                        send_whatsapp_message(final_notice.contact, final_notice.name, final_notice.email, final_notice.price)              
                    
            self.stdout.write(self.style.SUCCESS('Twilio sent final notice successfully'))
            
        except Exception as e:
            sms_logger.error(f'Error in handle method: {e}')
            self.stdout.write(self.style.ERROR('Failed to send  twilio final notices'))
