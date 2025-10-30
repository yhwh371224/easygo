import os
import logging
from twilio.rest import Client
from decouple import config

# Configure logging
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sms_logger = logging.getLogger('sms')


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


def send_sms_notice(phone_number, message_body):
    """Send a regular SMS via Twilio."""
    formatted_number = format_phone_number(phone_number)
    if not formatted_number:
        sms_logger.error(f"Cannot send message: invalid phone number {phone_number}")
        return
    try:
        message = client.messages.create(
            body=message_body,
            from_=sms_from,
            to=formatted_number
        )
        sms_logger.info(f'SMS sent to {formatted_number}')
    except Exception as e:
        sms_logger.error(f'Failed to send SMS to {formatted_number}: {e}')


def send_whatsapp_message(phone_number, message_body):
    """Send a WhatsApp message via Twilio."""
    formatted_number = format_phone_number(phone_number)
    if not formatted_number:
        sms_logger.error(f"Cannot send message: invalid phone number {phone_number}")
        return
    try:
        message = client.messages.create(
            body=message_body,
            from_=whatsapp_from,
            to=f'whatsapp:{formatted_number}'
        )
        sms_logger.info(f'WhatsApp message sent to {formatted_number}')
    except Exception as e:
        sms_logger.error(f'Failed to send WhatsApp message to {formatted_number}: {e}')


