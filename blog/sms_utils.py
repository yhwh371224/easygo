import os
import logging
from twilio.rest import Client
from decouple import config

# Configure logging
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sms_logger = logging.getLogger('sms')

# Initialize Twilio client
account_sid = config('TWILIO_ACCOUNT_SID')
auth_token = config('TWILIO_AUTH_TOKEN')
client = Client(account_sid, auth_token)

def format_phone_number(phone_number):
    if not phone_number.startswith('+'):
        phone_number = '+61' + phone_number.lstrip('0')
    return phone_number

def send_sms_notice(phone_number, message_body):
    formatted_number = format_phone_number(phone_number)
    try:
        message = client.messages.create(
            body=message_body,
            from_='+18148920523',  
            to=formatted_number
        )
        sms_logger.info(f'SMS sent to {formatted_number}')
    except Exception as e:
        sms_logger.error(f'Failed to send SMS to {formatted_number}: {e}')
