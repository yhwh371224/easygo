from datetime import datetime, date

def parse_future_date(date_str, field_name="date", required=True):
    """
    YYYY-MM-DD 또는 Month Day, Year 형식의 날짜를 파싱하고,
    오늘 이전 날짜면 ValueError 발생
    :param date_str: 문자열
    :param field_name: 필드명 (오류 메시지용)
    :param required: True이면 값이 없으면 오류
    :return: datetime.date 객체
    """
    if not date_str or date_str.strip() == "":
        if required:
            raise ValueError(f"{field_name} is required.")
        return None

    # ================= Debug =================
    print(f"[DEBUG] Raw {field_name}: {repr(date_str)}")

    # 마침표 제거 후 공백 정리
    clean_date_str = date_str.replace('.', '').strip()

    parsed_date = None
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
