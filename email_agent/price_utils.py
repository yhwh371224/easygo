from basecamp.area_full import get_more_suburbs


def calculate_pickup_time(direction, flight_time=None, pickup_time=None):
    from datetime import datetime, timedelta

    if pickup_time:
        return pickup_time

    if not flight_time or not direction:
        return None

    ft = datetime.strptime(flight_time, "%H:%M")

    offsets = {
        'Pickup from Intl Airport':     timedelta(hours=1),
        'Pickup from Domestic Airport': timedelta(minutes=30),
        'Drop off to Intl Airport':     -timedelta(hours=4),
        'Drop off to Domestic Airport': -timedelta(hours=2, minutes=30),
    }

    offset = offsets.get(direction)
    if offset is None:
        return None

    return (ft + offset).strftime("%H:%M")


def calculate_price(suburb_name, passengers, direction, large_luggage=0, medium_small_luggage=0,
                    bike=0, ski=0, snow_board=0, golf_bag=0, musical_instrument=0, carton_box=0):
    suburbs = get_more_suburbs()

    if suburb_name not in suburbs:
        return None

    sub = int(suburbs[suburb_name]['price'])
    no_p = int(passengers)

    drop_off = ['Drop off to Domestic Airport', 'Drop off to Intl Airport']
    pickup = ['Pickup from Domestic Airport', 'Pickup from Intl Airport', 'Cruise transfers or Point to Point']

    if direction in drop_off:
        base_price = sub + (no_p * 10) - 10 if 1 <= no_p < 10 else sub + (no_p * 10) + 10
    elif direction in pickup:
        base_price = sub + (no_p * 10) if 1 <= no_p < 10 else sub + (no_p * 10) + 10
    else:
        return None

    extra_large = max(0, large_luggage - no_p)
    extra_medium_small = max(0, medium_small_luggage - no_p)
    luggage_surcharge = (extra_large + extra_medium_small) * 5

    # 특수 짐 추가요금
    special_surcharge = (bike + ski) * 20
    special_surcharge += (snow_board + golf_bag + musical_instrument + carton_box) * 10

    return base_price + luggage_surcharge


def calculate_luggage_surcharge(passengers, large_luggage, medium_small_luggage):
    allowed_large = passengers
    allowed_medium_small = passengers
    
    extra_large = max(0, large_luggage - allowed_large)
    extra_medium_small = max(0, medium_small_luggage - allowed_medium_small)
    
    return (extra_large + extra_medium_small) * 5