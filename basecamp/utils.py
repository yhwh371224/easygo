from datetime import datetime, date


def parse_date(date_str, field_name="Date", required=True, reference_date=None):

    if not date_str or date_str.strip() == "":
        if required:
            raise ValueError(f"'{field_name}' is a required field.")
        return None

    try:
        parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(f"Invalid date format for '{field_name}' ({date_str}). Please use YYYY-MM-DD.")

    if parsed_date <= date.today():
        raise ValueError(f"'{field_name}' must be a date after today ({date.today().strftime('%Y-%m-%d')}).")
        
    if reference_date and parsed_date < reference_date:
        ref_str = reference_date.strftime('%Y-%m-%d')
        raise ValueError(f"'{field_name}' ({parsed_date}) cannot be before the initial pickup date ({ref_str}).")

    return parsed_date

