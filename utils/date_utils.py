from datetime import datetime, date
from django.http import JsonResponse

def parse_future_date(date_str, field_name="date", required=True):
    """
    YYYY-MM-DD 또는 Month Day, Year 형식의 날짜를 파싱하고,
    오늘 이전 날짜면 오류를 반환
    브라우저에서 JSON으로 오류/디버그 확인 가능
    :param date_str: 문자열
    :param field_name: 필드명 (오류 메시지용)
    :param required: True이면 값이 없으면 오류
    :return: datetime.date 객체 또는 JsonResponse 오류
    """
    if not date_str or date_str.strip() == "":
        if required:
            return JsonResponse({'success': False, 'error': f"{field_name} is required."})
        return None

    # ================= Debug: 실제 들어오는 값 확인 =================
    debug_data = {'success': True, 'debug_pickup_date': date_str}

    # 여러 포맷 시도
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
            'debug_pickup_date': date_str,
            'error': f"Invalid format for {field_name}. Accepted formats: YYYY-MM-DD or 'Oct 21, 2025'."
        })

    if parsed_date <= date.today():
        return JsonResponse({
            'success': False,
            'debug_pickup_date': date_str,
            'error': f"You entered ({parsed_date}) | Pickup date must be a future date.\n\n"
                     f"Please select a valid date for your future pickup."
        })

    # 성공하면 파싱된 날짜 리턴
    return parsed_date
