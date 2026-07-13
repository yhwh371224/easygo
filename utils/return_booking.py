from blog.blog_utils import resolve_driver
from blog.models import Post, Driver
from regions.models import Region
from utils.prepay_helper import is_foreign_number


# Flight return booking
def handle_return_trip(instance):
    original_notice = instance.notice or ""

    if (
        instance.return_pickup_time == 'x' or  
        instance.sent_email or                
        instance.calendar_event_id or
        "===RETURN===" in original_notice
    ):
        return

    elif (
            not instance.calendar_event_id and 
            instance.return_pickup_time and
            "===RETURN===" not in original_notice  
        ):

        # 🔑 원본 instance 기준으로 prepay 판단
        prepay_val = instance.prepay or (
            is_foreign_number(instance.contact) or
            (instance.company_name or "").strip()
        )

        driver = instance.driver or resolve_driver(instance.suburb)

        price_raw = str(instance.price or '').strip()

        if price_raw in ('', 'TBA'):
            return

        try:
            full_price = float(price_raw)
        except ValueError:
            return

        half_price = round(full_price / 2, 2)

        # paid 처리
        full_paid_float = None
        half_paid = None
        if instance.paid:
            try:
                full_paid_float = round(float(instance.paid), 2)
                half_paid = round(full_paid_float / 2, 2)
            except ValueError:
                pass

        # driver_price 처리 — price/paid와 동일하게 반으로 나눔. 아직 자동
        # 채움 전이라 비어있으면 price 기준으로 취급.
        driver_price_raw = str(instance.driver_price or '').strip()
        try:
            full_driver_price = float(driver_price_raw) if driver_price_raw not in ('', 'TBA') else full_price
        except ValueError:
            full_driver_price = full_price
        half_driver_price = round(full_driver_price / 2, 2)

        # notice 생성
        notice_parts = [original_notice.strip(), f"===RETURN=== (Total Price: ${int(full_price)})"]

        if full_paid_float is not None:
            notice_parts.append(f"Total Paid: ${int(full_paid_float)}")
            
        updated_notice = " | ".join(filter(None, notice_parts)).strip()

        instance.price = half_price
        instance.paid = half_paid
        instance.driver_price = half_driver_price
        instance.notice = updated_notice

        Post.objects.filter(id=instance.id).update(
            price=half_price,
            paid=half_paid,
            driver_price=half_driver_price,
            notice=updated_notice
        )

        # ✅ return_start_point / return_end_point 처리
        return_start_val = instance.return_start_point or ""
        return_end_val = instance.return_end_point or ""

        # ✅ suburb/street은 무조건 instance 값 유지
        street_val = instance.street or ""
        suburb_val = instance.suburb or ""

        region = instance.region

        # Post 생성에 필요한 필드들을 **kwargs로 묶음
        post_fields = {
            'booker_name': instance.booker_name,
            'booker_email': instance.booker_email,
            'booker_contact': instance.booker_contact,
            'name': instance.name,
            'contact': instance.contact,
            'email': instance.email,
            'company_name': instance.company_name,
            'email1': instance.email1,
            'pickup_date': instance.return_pickup_date,
            'flight_number': instance.return_flight_number,
            'flight_time': instance.return_flight_time,
            'pickup_time': instance.return_pickup_time,
            'direction': instance.return_direction,
            'start_point': return_start_val,
            'end_point': return_end_val,
            'suburb': suburb_val,
            'street': street_val,
            'no_of_passenger': instance.no_of_passenger,
            'no_of_baggage': instance.no_of_baggage,
            'message': instance.message,
            'return_pickup_time': "x",
            'return_pickup_date': instance.pickup_date,
            'notice': updated_notice,
            'cash': instance.cash,
            'prepay': bool(prepay_val),
            'price': half_price,
            'paid': half_paid,
            'driver_price': half_driver_price,
            'private_ride': instance.private_ride,
            'toll': instance.toll,
            'surcharge': instance.surcharge,
            'driver': driver,
            'region': region,
            'extra_stop': instance.extra_stop,
            'same_extra_stop': instance.same_extra_stop,
            'extra_stop_addresses': instance.extra_stop_addresses if instance.same_extra_stop else [],
            'special_items': instance.special_items or {},
        }

        Post.objects.create(**post_fields)


        