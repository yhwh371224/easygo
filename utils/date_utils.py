from datetime import datetime, date

def parse_future_date(date_str, field_name="date", required=True):
    """
    YYYY-MM-DD 형식의 날짜를 파싱하고, 오늘 이전 날짜는 오류 처리
    :param date_str: 문자열
    :param field_name: 필드명 (오류 메시지용)
    :param required: True이면 값이 없으면 오류
    :return: datetime.date 객체 또는 None
    """
    if not date_str or date_str.strip() == "":
        if required:
            raise ValueError(f"{field_name} is required.")
        return None  # 값이 없으면 None 리턴

    parsed_date = None
    for fmt in ("%Y-%m-%d", "%b %d, %Y"):
        try:
            parsed_date = datetime.strptime(date_str.strip(), fmt).date()
            break
        except ValueError:
            continue

    if not parsed_date:
        raise ValueError(f"Invalid format for {field_name}. Accepted formats: YYYY-MM-DD or 'Oct 21, 2025'.")
    
    if parsed_date <= date.today():
        raise ValueError(
            f"You entered ({parsed_date}) | Pickup date must be a future date.\n\n"
            f"Please select a valid date for your future pickup."
        )

    return parsed_date
