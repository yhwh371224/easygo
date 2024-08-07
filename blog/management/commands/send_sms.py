import os
from twilio.rest import Client
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from blog.models import Post
from decouple import config


class Command(BaseCommand):
    help = 'Send final notices via WhatsApp or SMS'

    def handle(self, *args, **options):
        tomorrow = date.today() + timedelta(days=1)
        final_notices = Post.objects.filter(pickup_date=tomorrow)
        
        # Initialize Twilio client once
        account_sid = config('TWILIO_ACCOUNT_SID')
        auth_token = config('TWILIO_AUTH_TOKEN')
        client = Client(account_sid, auth_token)

        # List of office numbers
        office_numbers = [
            '+61406883355',  
        ]

        def format_phone_number(phone_number):
            if not phone_number.startswith('+'):
                phone_number = '+61' + phone_number.lstrip('0')
            return phone_number

        def send_whatsapp_message(sendto):
            formatted_number = format_phone_number(sendto)
            message = client.messages.create(
                body="EasyGo - Urgent notice \
                      \n\nWe haven't received your payment and a response to our emails. \
                      \nPlease email us ASAP to ensure your booking remains confirmed \
                      \nReply only via email >> info@easygoshuttle.com.au",
                from_='whatsapp:+14155238886',  # Your Twilio WhatsApp-enabled number
                to=f'whatsapp:{formatted_number}'
            )
            

        def send_sms_message(sendto, message_body):
            formatted_number = format_phone_number(sendto)
            message = client.messages.create(
                body=message_body,
                from_='+18148920523',  # Your Twilio SMS number
                to=formatted_number
            )
            

        sent_numbers = []  
        for final_notice in final_notices:
            if not final_notice.reminder and not final_notice.cancelled and not final_notice.paid:
                if final_notice.direction == 'Pickup from Intl Airport':
                    send_whatsapp_message(final_notice.contact)
                else:
                    message_body = "EasyGo - Urgent notice \
                                    \n\nWe haven't received your payment and a response to our emails. \
                                    \nPlease email us ASAP to ensure your booking remains confirmed \
                                    \nReply only via email >> info@easygoshuttle.com.au"
                    send_sms_message(final_notice.contact, message_body)
                
                if final_notice.contact:
                    sent_numbers.append(final_notice.contact)  # Just store the phone numbers

        # Prepare log message to be sent to office numbers
        log_message = "\n".join([f'Twilio message sent to {number}' for number in sent_numbers])
        for office_number in office_numbers:
            send_sms_message(office_number, log_message)

        self.stdout.write(self.style.SUCCESS('Successfully sent final notices via twilio'))
