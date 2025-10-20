from datetime import datetime

def parse_date_safe(value, field_name, required=True):
    """
    Parse a date safely from various formats.
    If required=False and value is empty, returns None instead of raising an error.
    """
    if not value or value.strip() == "":
        if required:
            raise ValueError(f"{field_name} is required.")
        return None  # ✅ allow empty optional dates

    formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]

    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Invalid format for {field_name}. Use YYYY-MM-DD.")

