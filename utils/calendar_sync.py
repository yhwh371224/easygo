import logging
import datetime
import re

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from django.conf import settings
from blog.models import Post
from blog.sms_utils import normalize_phone

logger = logging.getLogger(__name__)


def _get_contact_display(instance):
    from blog.models import PhoneMapping
    if getattr(instance, 'use_proxy', False):
        customer_phone = normalize_phone(instance.contact)
        if PhoneMapping.objects.filter(from_number=customer_phone).exists():
            return settings.BIRD_NUMBER
    return instance.contact


SCOPES = ['https://www.googleapis.com/auth/calendar']

_UNSET = object()

def get_calendar_service(subject=_UNSET):
    service_account_file = settings.CALENDAR_SERVICE_ACCOUNT_FILE

    # 명시적으로 None을 넘긴 경우 → 서비스 계정 직접 접근 (드라이버용)
    # 아무것도 안 넘긴 경우 → settings에서 기본값 읽기 (회사 캘린더용)
    if subject is _UNSET:
        subject = getattr(settings, 'RECIPIENT_EMAIL', None)

    kwargs = {'scopes': SCOPES}
    if subject:
        kwargs['subject'] = subject

    credentials = service_account.Credentials.from_service_account_file(
        service_account_file, **kwargs
    )
    return build('calendar', 'v3', credentials=credentials)


def abbreviate_baggage(baggage_str):
    """Baggage string을 짧게 줄이기 (Oversize -> o, label 줄이기)"""
    if not baggage_str:
        return ""

    # ✅ 4번: 긴 라벨을 먼저 치환하도록 OrderedDict 대신 리스트로 순서 보장
    # (짧은 패턴이 먼저 매칭돼서 긴 라벨이 깨지는 것을 방지)
    label_map = [
        ("Booster", "Bt"),
        ("Oversize", "o"),  # 괄호 없이도 대응
        ("Music", "Mu"),
        ("Baby", "Bb"),
        ("Snow", "Sn"),
        ("Golf", "Gf"),
        ("Bike", "Bk"),
        ("Pram", "Pr"),
        ("Ski", "Sk"),
        ("Box", "Bx"),
        ("L", "L"),
        ("M", "M"),
        ("S", "S"),
    ]

    items = [item.strip() for item in baggage_str.split(",") if item.strip()]

    short_items = []
    for item in items:
        # ✅ 4번: 각 아이템을 순서대로 한 번씩만 치환 (재매칭 방지)
        for long_label, abbr in label_map:
            pattern = r"\b" + re.escape(long_label) + r"\b"
            item = re.sub(pattern, abbr, item, count=1, flags=re.IGNORECASE)

        # (Oversize) 형태도 별도 처리
        item = re.sub(r"\(\s*Oversize\s*\)", "(o)", item, flags=re.IGNORECASE)

        short_items.append(item)

    short_baggage_str = ", ".join(short_items)
    if len(short_baggage_str) > 60:
        short_baggage_str = short_baggage_str[:60] + "..."
    return short_baggage_str


def _build_common(instance, contact_display=None):
    """title, address, start/end 등 두 캘린더가 공유하는 공통 필드 계산.
    날짜/시간 파싱 실패 시 None 반환."""
    if contact_display is None:
        contact_display = instance.contact

    title = " ".join(filter(None, [
        '!' if instance.reminder else '',
        'C' if instance.cancelled else '',
        '?' if instance.pending or instance.price == 'TBA' else '',
        instance.pickup_time or '',
        instance.flight_number or '',
        instance.start_point or '',
        instance.flight_time or '',
        f'p{instance.no_of_passenger}' if instance.no_of_passenger else '',
        'paid' if instance.paid else '',
        'cash' if instance.cash and not instance.paid else '',
        f'${instance.price}' if instance.price else '',
        contact_display or '',
    ])).strip()

    suburb_str = instance.suburb or ''
    street_str = instance.street or ''
    end_point_str = instance.end_point or ''
    if suburb_str and street_str:
        address = f"{street_str} {suburb_str}"
    elif street_str:
        # suburb 없을 때 end_point를 보조 지역명으로 사용
        address = f"{street_str} {end_point_str}"
    elif suburb_str:
        address = suburb_str
    else:
        address = end_point_str

    try:
        pickup_date = datetime.datetime.strptime(str(instance.pickup_date), "%Y-%m-%d")
        pickup_time = datetime.datetime.strptime(instance.pickup_time or "00:00", "%H:%M")
    except Exception as e:
        logger.error(f"Invalid pickup date/time for post {instance.id}: {e}")
        return None

    start = datetime.datetime.combine(pickup_date, pickup_time.time())
    end = start + datetime.timedelta(hours=1)

    return {
        "title": title,
        "address": address,
        "start": start,
        "end": end,
    }


def build_event_data(instance):
    """회사 캘린더용 event body 생성"""
    contact_display = _get_contact_display(instance)
    common = _build_common(instance, contact_display=contact_display)
    if common is None:
        return None

    baggage_str = abbreviate_baggage(instance.no_of_baggage)
    message = " ".join(filter(None, [
        instance.name,
        instance.email,
        f"b:{baggage_str}" if baggage_str else "",
        f"t:{instance.toll}" if instance.toll else "",
        f"m:{instance.message}" if instance.message else "",
        f"n:{instance.notice}" if instance.notice else "",
        f"d:{instance.return_pickup_date}" if instance.return_pickup_date else "",
        f"${instance.paid}" if instance.paid else "",
        "private" if instance.private_ride else "",
        f"end.:{instance.end_point}" if instance.end_point else "",
        instance.contact if contact_display != instance.contact else '',
    ]))

    return {
        "summary": common["title"],
        "location": common["address"],
        "start": {"dateTime": common["start"].strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "Australia/Sydney"},
        "end": {"dateTime": common["end"].strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "Australia/Sydney"},
        "description": message,
    }


def build_driver_event_data(instance):
    """드라이버 캘린더용 event body 생성 (간결한 설명)"""
    common = _build_common(instance, contact_display=_get_contact_display(instance))
    if common is None:
        return None

    baggage_str = abbreviate_baggage(instance.no_of_baggage)
    description = " ".join(filter(None, [
        instance.name or '',
        f"b:{baggage_str}" if baggage_str else "",
        instance.message or '',
        instance.end_point or '',
    ]))

    return {
        "summary": common["title"],
        "location": common["address"],
        "start": {"dateTime": common["start"].strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "Australia/Sydney"},
        "end": {"dateTime": common["end"].strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "Australia/Sydney"},
        "description": description,
    }


def delete_from_calendar(calendar_id, event_id):
    """캘린더에서 이벤트 삭제 (서비스 계정 직접 접근, delegation 없음)"""
    service = get_calendar_service(subject=None)
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        logger.info(f"Deleted event {event_id} from calendar {calendar_id}")
    except HttpError as e:
        # ✅ 5번: 404(이미 삭제된 이벤트)는 warning, 그 외는 error
        if e.resp.status == 404:
            logger.warning(f"Event {event_id} not found in calendar {calendar_id} (already deleted?)")
        else:
            logger.error(f"Calendar delete failed (calendar: {calendar_id}, event: {event_id}): {e}")
    except Exception as e:
        logger.error(f"Calendar delete failed (calendar: {calendar_id}, event: {event_id}): {e}")


def sync_to_calendar(instance, calendar_id="primary", is_driver=False):
    service = get_calendar_service(subject=None) if is_driver else get_calendar_service()
    event = build_driver_event_data(instance) if is_driver else build_event_data(instance)
    if not event:
        return

    event_id = (
        (instance.driver_calendar_event_id or "").strip()
        if is_driver
        else (instance.calendar_event_id or "").strip()
    )

    try:
        if event_id:
            try:
                service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
            except HttpError as e:
                # ✅ 6번: 이벤트가 Google에서 삭제된 경우 insert로 폴백
                if e.resp.status == 404:
                    logger.warning(
                        f"Event {event_id} not found for post {instance.id}, falling back to insert"
                    )
                    event_id = ""  # 아래 insert 분기로 진행
                else:
                    raise
        
        if not event_id:
            new_event = service.events().insert(calendarId=calendar_id, body=event).execute()
            new_event_id = new_event["id"]

            if is_driver:
                Post.objects.filter(pk=instance.pk).update(driver_calendar_event_id=new_event_id)
                # ✅ 1번: 메모리상 인스턴스도 동기화
                instance.driver_calendar_event_id = new_event_id
            else:
                Post.objects.filter(pk=instance.pk).update(calendar_event_id=new_event_id)
                # ✅ 1번: 메모리상 인스턴스도 동기화
                instance.calendar_event_id = new_event_id

    except Exception as e:
        logger.error(f"Calendar sync failed for post {instance.id} (calendar: {calendar_id}): {e}")