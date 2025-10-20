from datetime import datetime

def parse_date_safe(value, field_name):
    if not value:
        raise ValueError(f"{field_name} is required.")
    
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]
    
    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    
    raise ValueError(f"Invalid format for {field_name}. Use YYYY-MM-DD.")

