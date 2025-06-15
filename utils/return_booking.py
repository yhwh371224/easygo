from blog.models import Post


# Flight return booking
def handle_return_trip(instance):
    original_notice = instance.notice or ""

    if (
        instance.return_pickup_time == 'x' or  
        instance.sent_email or                
        instance.calendar_event_id or
        "Return trips:" in original_notice
    ):
        return

    elif not instance.calendar_event_id and instance.return_pickup_time:
        full_price = float(instance.price or 0)
        half_price = round(full_price / 2, 2)
        full_paid = float(instance.paid or 0)
        half_paid = round(full_paid / 2, 2)

        # notice 메시지 생성        
        notice_parts = [original_notice.strip(), f"Return trips: ${full_price:.2f}"]
        if full_paid > 0:
            notice_parts.append(f"Total Paid: ${full_paid:.2f}")

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
                 notice=updated_notice, price=half_price, paid=half_paid, private_ride=instance.private_ride, driver=instance.driver,)

        p.save() 