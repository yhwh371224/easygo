import logging
import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account
from django.conf import settings

logger = logging.getLogger(__name__)

# 기본 Google Calendar 설정
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'secure/calendar/calendar-service-account-file.json'
DELEGATED_USER_EMAIL = getattr(settings, 'RECIPIENT_EMAIL', None)

# 1️⃣ Google Calendar 인증 서비스 생성
def get_calendar_service():
    """Google Calendar API 서비스 객체 생성"""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES, subject=DELEGATED_USER_EMAIL
    )
    service = build('calendar', 'v3', credentials=credentials)
    return service

# 2️⃣ event 데이터 구성
def build_event_data(instance):
    """Post instance로부터 Google Calendar event body 생성"""
    reminder_str = '!' if instance.reminder else ''
    cancelled_str = 'C' if instance.cancelled else ''
    pending_str = '?' if instance.price == 'TBA' else ''
    pickup_time_str = instance.pickup_time or ''
    flight_number_str = instance.flight_number or ''
    start_point_str = instance.start_point or ''
    flight_time_str = instance.flight_time or ''
    no_of_passenger_str = f'p{instance.no_of_passenger}' if instance.no_of_passenger else ''
    paid_str = 'paid' if instance.paid else ''
    cash_str = 'cash' if instance.cash else ''
    toll_str = 'toll' if instance.toll else ''
    price_str = f'${instance.price}' if instance.price else ''
    contact_str = instance.contact or ''
    suburb_str = instance.suburb or ''
    street_str = instance.street or ''
    end_point_str = instance.end_point or ''

    title = " ".join(filter(None, [
        reminder_str,
        cancelled_str,
        pending_str,
        pickup_time_str,
        flight_number_str,
        start_point_str,
        flight_time_str,
        no_of_passenger_str,
        paid_str,
        cash_str,
        price_str,
        contact_str,
    ])).strip()

    # 주소
    if suburb_str and street_str:
        address = f"{street_str} {suburb_str}"
    elif street_str:
        address = f"{street_str} {end_point_str}"
    elif suburb_str:
        address = suburb_str
    else:
        address = end_point_str

    # 설명 (message)
    message_parts = [
        instance.name,
        instance.email,
        f"b:{instance.no_of_baggage}" if instance.no_of_baggage else "",
        f"t:{instance.toll}" if instance.toll else "",
        f"m:{instance.message}" if instance.message else "",
        f"n:{instance.notice}" if instance.notice else "",
        f"d:{instance.return_pickup_date}" if instance.return_pickup_date else "",
        f"${instance.paid}" if instance.paid else "",
        "private" if instance.private_ride else "",
        f"opt:{instance.end_point}" if instance.end_point else "",
    ]
    message = " ".join(filter(None, message_parts))

    # 날짜 및 시간
    try:
        pickup_date = datetime.datetime.strptime(str(instance.pickup_date), "%Y-%m-%d")
    except Exception as e:
        logger.error(f"Invalid pickup_date for post {instance.id}: {e}")
        return None

    try:
        pickup_time = datetime.datetime.strptime(instance.pickup_time or "00:00", "%H:%M")
    except Exception as e:
        logger.error(f"Invalid pickup_time for post {instance.id}: {e}")
        return None

    start = datetime.datetime.combine(pickup_date, pickup_time.time())
    end = start + datetime.timedelta(hours=1)

    event = {
        "summary": title,
        "location": address,
        "start": {
            "dateTime": start.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": "Australia/Sydney",
        },
        "end": {
            "dateTime": end.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": "Australia/Sydney",
        },
        "description": message,
    }

    return event


# 3️⃣ Google Calendar에 반영
def sync_to_calendar(instance):
    """Post instance를 Google Calendar와 동기화"""
    service = get_calendar_service()
    event = build_event_data(instance)
    if not event:
        return  # event 생성 실패 시 중단

    event_id = (instance.calendar_event_id or "").strip()

    try:
        if event_id:
            service.events().update(
                calendarId="primary", eventId=event_id, body=event
            ).execute()
        else:
            new_event = service.events().insert(
                calendarId="primary", body=event
            ).execute()
            instance.calendar_event_id = new_event["id"]
            instance.save(update_fields=["calendar_event_id"])
    except Exception as e:
        logger.error(f"Calendar sync failed for post {instance.id}: {e}")

