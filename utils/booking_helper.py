import logging
from datetime import date
from blog.models import Post

logger = logging.getLogger(__name__)

def update_meeting_point_for_international_arrivals():
    """
    오늘 국제선 도착 예약 중에서 flight_time 순서로 정렬.
    첫 번째 예약은 그대로 두고, 나머지는 meeting_point가 비어있으면 'Rideshare'로 업데이트.
    """
    today = date.today()

    today_arrivals = Post.objects.filter(
        pickup_date=today,
        direction="Pickup from Intl Airport",
        cancelled=False
    ).order_by('flight_time')

    first = True
    for booking in today_arrivals:
        if first:
            first = False
            continue

        # meeting_point가 이미 있으면 건드리지 않음
        if not booking.meeting_point or booking.meeting_point.strip() == "":
            booking.meeting_point = "Rideshare"
            booking.save(update_fields=['meeting_point'])
            logger.info(f"Updated meeting_point to Rideshare for {booking.name} ({booking.flight_time})")
        else:
            logger.info(f"Skipped {booking.name} ({booking.flight_time}) – meeting_point already set")
