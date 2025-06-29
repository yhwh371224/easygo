from blog.models import Post
from blog.models import Driver

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

        price_raw = (instance.price or '').strip()

        try:
            full_price = float(price_raw) if price_raw else 0.0
        except ValueError:
            full_price = 0.0  

        half_price = round(full_price / 2, 2)

        # paid 처리
        full_paid = instance.paid
        half_paid = None
        if full_paid:
            try:
                full_paid_float = round(float(full_paid), 2)
                half_paid = round(full_paid_float / 2, 2)
            except ValueError:
                full_paid_float = None
                half_paid = None
        else:
            full_paid_float = None

        # notice 생성
        notice_parts = [original_notice.strip(), f"===RETURN=== (Total Price: ${int(full_price)})"]

        if full_paid_float is not None:
            notice_parts.append(f"Total Paid: ${int(full_paid_float)}")
            
        updated_notice = " | ".join(filter(None, notice_parts)).strip()

        instance.price = half_price
        instance.paid = half_paid
        instance.notice = updated_notice
        instance.save(update_fields=['price', 'paid', 'notice'])

        p = Post(name=instance.name, contact=instance.contact, email=instance.email, company_name=instance.company_name, email1=instance.email1, 
                 pickup_date=instance.return_pickup_date, flight_number=instance.return_flight_number, flight_time=instance.return_flight_time, 
                 pickup_time=instance.return_pickup_time, direction=instance.return_direction, start_point=instance.return_start_point, 
                 end_point=instance.return_end_point, suburb=instance.suburb, street=instance.street, no_of_passenger=instance.no_of_passenger, 
                 no_of_baggage=instance.no_of_baggage, message=instance.message, return_pickup_time="x", return_pickup_date=instance.pickup_date, 
                 notice=updated_notice, price=half_price, paid=half_paid, private_ride=instance.private_ride, driver=driver,)

        p.save() 

        