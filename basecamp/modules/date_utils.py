from datetime import datetime, date


def parse_date(date_str, field_name="Date", required=True, reference_date=None):
    if isinstance(date_str, date):
        return date_str

    if not date_str or str(date_str).strip() == "":
        if required:
            raise ValueError(f"'{field_name}' is a required field.")
        return None

    try:
        parsed_date = datetime.strptime(str(date_str), '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(f"Invalid date format for '{field_name}' ({date_str}). Please use YYYY-MM-DD.")

    if parsed_date <= date.today():
        raise ValueError(f"'{field_name}' cannot be in the past ({date.today().strftime('%Y-%m-%d')}).")

    if reference_date and parsed_date < reference_date:
        ref_str = reference_date.strftime('%Y-%m-%d')
        raise ValueError(f"'{field_name}' ({parsed_date}) cannot be before the initial pickup date ({ref_str}).")

    return parsed_date


def parse_booking_dates(pickup_str, return_str=None):
    pickup_date_obj = parse_date(pickup_str, field_name="Pickup Date", required=True)
    return_pickup_date_obj = parse_date(
        return_str, field_name="Return Pickup Date", required=False, reference_date=pickup_date_obj
    )
    return pickup_date_obj, return_pickup_date_obj


def format_pickup_time_12h(pickup_time_str):
    try:
        time_obj = datetime.strptime(pickup_time_str.strip(), "%H:%M")
        return time_obj.strftime("%I:%M %p")
    except ValueError:
        return pickup_time_str
