from datetime import datetime

def parse_date_safe(value, field_name):
    """
    Parse a date from YYYY-MM-DD format.
    If value is empty, returns None instead of raising an error.
    """
    if not value or value.strip() == "":
        return None  # 빈 값이면 그냥 None 반환

    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid format for {field_name}. Use YYYY-MM-DD.")



