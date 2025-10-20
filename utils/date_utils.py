from datetime import datetime, date
from datetime import datetime, date

def parse_future_date(date_str, field_name="date", required=True):
    if not date_str or date_str.strip() == "":
        if required:
            raise ValueError(f"{field_name} is required.")
        return None
    
    # 마침표 제거
    clean_date_str = date_str.replace('.', '').strip()

    parsed_date = None
    # 여러 포맷 시도
    for fmt in ("%Y-%m-%d", "%b %d, %Y", "%d %b, %Y", "%B %d, %Y", "%d %B, %Y"):
        try:
            parsed_date = datetime.strptime(clean_date_str, fmt).date()
            break
        except ValueError:
            continue

    if not parsed_date:
        raise ValueError(
            f"Invalid format for {field_name}: {repr(date_str)}. "
            f"Accepted formats: YYYY-MM-DD or 'Oct 21, 2025'."
        )

    if parsed_date <= date.today():
        raise ValueError(
            f"You entered ({parsed_date}) | Pickup date must be a future date.\n\n"
            f"Please select a valid date for your future pickup."
        )

    return parsed_date