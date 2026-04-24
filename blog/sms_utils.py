import logging
import json

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from decouple import config

import phonenumbers
from phonenumbers import NumberParseException


# =========================
# Logging
# =========================
sms_logger = logging.getLogger('sms')


# =========================
# Twilio Lazy Init
# =========================
_client = None

def get_client():
    global _client
    if _client is None:
        _client = Client(config('TWILIO_ACCOUNT_SID'), config('TWILIO_AUTH_TOKEN'))
    return _client


# =========================
# Phone Formatting
# =========================
def format_au_phone(number):
    """Convert +61XXXXXXXXX to 0XXX XXX XXX format."""
    if not number:
        return number
    number = str(number).strip().replace(' ', '')
    if number.startswith('+61'):
        number = '0' + number[3:]
    if len(number) == 10:
        return f"{number[:4]} {number[4:7]} {number[7:]}"
    return number


# =========================
# Phone Normalization (GLOBAL STANDARD)
# =========================
def normalize_phone(phone_number, default_region="AU"):
    """
    Convert any international/local number to E.164 format safely.
    Returns None if invalid.
    """
    if not phone_number:
        return None

    try:
        parsed = phonenumbers.parse(phone_number, default_region)

        if not phonenumbers.is_valid_number(parsed):
            return None

        return phonenumbers.format_number(
            parsed,
            phonenumbers.PhoneNumberFormat.E164
        )

    except NumberParseException:
        return None


# =========================
# SMS (Twilio)
# =========================
def send_sms_notice(phone_number, message_body):
    """
    Send SMS via Twilio.
    Returns message SID or None.
    """
    formatted_number = normalize_phone(phone_number)

    if not formatted_number:
        sms_logger.error(f"[SMS] Invalid phone number: {phone_number}")
        return None

    if not message_body:
        sms_logger.error(f"[SMS] Empty message body for {formatted_number}")
        return None

    try:
        message = get_client().messages.create(
            body=message_body,
            messaging_service_sid=config('TWILIO_MESSAGING_SERVICE_SID'),
            to=formatted_number
        )

        sms_logger.info(
            f"[SMS SENT] to={formatted_number} sid={message.sid}"
        )

        return message.sid

    except TwilioRestException as e:
        sms_logger.error(
            f"[SMS ERROR] Twilio error to={formatted_number} "
            f"status={e.status} code={e.code} msg={e.msg}"
        )
        return None

    except Exception as e:
        sms_logger.error(
            f"[SMS ERROR] Unexpected error to={formatted_number} error={str(e)}"
        )
        return None


# =========================
# WhatsApp (Twilio)
# =========================
def send_whatsapp_template(phone_number, user_name=None):
    """
    Send WhatsApp template message via Twilio.
    Returns message SID or None.
    """
    formatted_number = normalize_phone(phone_number)

    if not formatted_number:
        sms_logger.error(f"[WA] Invalid phone number: {phone_number}")
        return None

    try:
        message = get_client().messages.create(
            from_=f'whatsapp:{config("TWILIO_WHATSAPP_FROM")}',
            to=f'whatsapp:{formatted_number}',
            content_sid="HX247229bb2bb4e0bcc4fb17ad94fb17a8",
            content_variables=json.dumps({
                "1": user_name or "",
                "2": "info@easygoshuttle.com.au"
            })
        )

        sms_logger.info(
            f"[WA SENT] to={formatted_number} sid={message.sid}"
        )

        return message.sid

    except TwilioRestException as e:
        sms_logger.error(
            f"[WA ERROR] Twilio error to={formatted_number} "
            f"status={e.status} code={e.code} msg={e.msg}"
        )
        return None

    except Exception as e:
        sms_logger.error(
            f"[WA ERROR] Unexpected error to={formatted_number} error={str(e)}"
        )
        return None