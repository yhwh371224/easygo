from datetime import datetime

def parse_date_safe(value, field_name, required=True):
    if not value or value.strip() == "":
        if required:
            raise ValueError(f"{field_name} is required.")
        return None  # ✅ optional date
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid format for {field_name}. Use YYYY-MM-DD.")



