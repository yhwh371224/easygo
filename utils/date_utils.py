from datetime import datetime, date
from django.http import JsonResponse

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
            return JsonResponse({'success': False, 'error': f"{field_name} is required."})
        return None

    # ================= Debug: 실제 들어오는 값 확인 =================
    # 브라우저로 확인할 수 있게 JSON으로 바로 반환
    return JsonResponse({'success': True, 'debug_pickup_date': date_str})

    # 기존 파싱 로직은 잠시 주석 처리
    """
    parsed_date = None
    for fmt in ("%Y-%m-%d", "%b %d, %Y", "%d %b, %Y", "%B %d, %Y", "%d %B, %Y"):
        try:
            parsed_date = datetime.strptime(date_str.strip(), fmt).date()
            break
        except ValueError:
            continue

    if not parsed_date:
        return JsonResponse({
            'success': False,
            'error': f"Invalid format for {field_name}. Accepted formats: YYYY-MM-DD or 'Oct 21, 2025'."
        })

    if parsed_date <= date.today():
        return JsonResponse({
            'success': False,
            'error': f"You entered ({parsed_date}) | Pickup date must be a future date.\n\nPlease select a valid date for your future pickup."
        })

    return parsed_date
    """

