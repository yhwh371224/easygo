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
        bookings = list(
            Post.objects.filter(
                pickup_date=today,
                direction=rule["direction"],
                cancelled=False,
            ).order_by("flight_time")
        )

        if not bookings:
            continue

        has_primary = any(
            b.meeting_point == rule["primary_value"]
            for b in bookings
        )

        for booking in bookings:
            if booking.meeting_point and booking.meeting_point.strip():
                continue

            # 1️⃣ primary 값이 아직 없으면 첫 번째 빈 값에 설정
            if not has_primary:
                booking.meeting_point = rule["primary_value"]
                has_primary = True

                logger.info(
                    f"Set first {rule['primary_value']} for "
                    f"{booking.name} ({booking.flight_time})"
                )
            else:
                # 2️⃣ primary 이후는 secondary 값
                booking.meeting_point = rule["secondary_value"]

                logger.info(
                    f"Set {rule['secondary_value']} for "
                    f"{booking.name} ({booking.flight_time})"
                )

            booking.save(update_fields=["meeting_point"])
