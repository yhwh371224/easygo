import logging
from datetime import date
from blog.models import Post

logger = logging.getLogger(__name__)

def update_meeting_point_for_arrivals():
    today = date.today()

    rules = [
        {
            "direction": "Pickup from Intl Airport",
            "primary_value": "Public",
            "secondary_value": "Rideshare",
        },
        {
            "direction": "Pickup from Domestic Airport",
            "primary_value": "Express",
            "secondary_value": "Priority",
        },
    ]

    for rule in rules:
        bookings = Post.objects.filter(
            pickup_date=today,
            direction=rule["direction"],
            cancelled=False
        ).order_by("flight_time")

        first = True  # 빈값 기준으로 첫 번째는 primary

        for booking in bookings:
            if booking.meeting_point and booking.meeting_point.strip():
                continue  # 이미 값이 있으면 건너뜀

            if first:
                booking.meeting_point = rule["primary_value"]
                first = False
                logger.info(f"Set first {rule['primary_value']} for {booking.name} ({booking.flight_time})")
            else:
                booking.meeting_point = rule["secondary_value"]
                logger.info(f"Set {rule['secondary_value']} for {booking.name} ({booking.flight_time})")

            booking.save(update_fields=["meeting_point"])
