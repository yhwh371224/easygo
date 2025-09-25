from datetime import datetime

def parse_date_safe(date_str, field_name="date"):
    """
    Safely parse a string into a date object.
    Returns None if the string is empty.
    Raises ValueError if the format is invalid.
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(f'Invalid format for {field_name}. Use YYYY-MM-DD.')
