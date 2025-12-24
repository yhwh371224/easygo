import logging
from datetime import date
from blog.models import Post

logger = logging.getLogger(__name__)

def update_meeting_point_for_international_arrivals():
    """
    오늘 도착 예약 처리
    - 국제선: flight_time 순, 첫 예약 보호, 나머지 → Rideshare
    - 국내선: flight_time 순, 첫 예약 보호, 나머지 → Priority pickup
    """
    today = date.today()

    directions = [
        ("Pickup from Intl Airport", "Rideshare"),
        ("Pickup from Domestic Airport", "Priority pickup"),
    ]

    for direction, default_meeting_point in directions:
        arrivals = (
            Post.objects.filter(
                pickup_date=today,
                direction=direction,
                cancelled=False
            )
            .order_by("flight_time")
        )

        first = True
        for booking in arrivals:
            if first:
                first = False
                logger.info(
                    f"First booking kept as-is ({direction}): "
                    f"{booking.name} ({booking.flight_time})"
                )
                continue

            if not booking.meeting_point or booking.meeting_point.strip() == "":
                booking.meeting_point = default_meeting_point
                booking.save(update_fields=["meeting_point"])
                logger.info(
                    f"Updated meeting_point to {default_meeting_point} "
                    f"for {booking.name} ({booking.flight_time})"
                )
            else:
                logger.info(
                    f"Skipped {booking.name} ({booking.flight_time}) – meeting_point already set"
                )
