from blog.models import Post, Driver


# ✅ street/suburb 처리 함수
def filter_value(value, start_point, end_point):
    if not value:
        return ""
    value_lower = value.lower()
    if (start_point and value_lower in start_point.lower()) or (end_point and value_lower in end_point.lower()):
        return value
    return ""

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

        driver = instance.driver or Driver.objects.get(driver_name__iexact="Sam")

        price_raw = str(instance.price or '').strip()

        try:
            full_price = float(price_raw) if price_raw else 0.0
        except ValueError:
            full_price = 0.0  

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

        # notice 생성
        notice_parts = [original_notice.strip(), f"===RETURN=== (Total Price: ${int(full_price)})"]

        if full_paid_float is not None:
            notice_parts.append(f"Total Paid: ${int(full_paid_float)}")
            
        updated_notice = " | ".join(filter(None, notice_parts)).strip()

        instance.price = half_price
        instance.paid = half_paid
        instance.notice = updated_notice
        instance.save(update_fields=['price', 'paid', 'notice'])

        # ✅ return_start_point / return_end_point 있으면 street, suburb를 빈문자열로
        # 단, start_point나 end_point 안에 street/suburb 이름이 있으면 그대로 유지
        street_val = filter_value(instance.street, instance.return_start_point, instance.return_end_point)
        suburb_val = filter_value(instance.suburb, instance.return_start_point, instance.return_end_point)

        # Post 생성에 필요한 필드들을 **kwargs로 묶음
        post_fields = {
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
            'start_point': instance.return_start_point,
            'end_point': instance.return_end_point,
            'suburb': suburb_val,
            'street': street_val,
            'no_of_passenger': instance.no_of_passenger,
            'no_of_baggage': instance.no_of_baggage,
            'message': instance.message,
            'return_pickup_time': "x",
            'return_pickup_date': instance.pickup_date,
            'notice': updated_notice,
            'price': half_price,
            'paid': half_paid,
            'private_ride': instance.private_ride,
            'toll': instance.toll,
            'driver': driver,
        }

        Post.objects.create(**post_fields)


        