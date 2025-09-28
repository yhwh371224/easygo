import requests, logging

from django.http import JsonResponse
from django.shortcuts import render
from decimal import Decimal, ROUND_HALF_UP
from main.settings import RECIPIENT_EMAIL
from .models import XrpPayment, Post

from .tasks import send_xrp_internal_email, send_xrp_customer_email


logger = logging.getLogger(__name__)

XRP_ADDRESS = "r9WZsBV3fhdHgXEkiJwGUDdgQJztGkYRGB"

def email_to_tag(email: str) -> int:
    """이메일 기반 32비트 Destination Tag 생성"""
    import hashlib
    hash_int = int(hashlib.md5(email.encode()).hexdigest(), 16)
    return hash_int % (2**32)

def xrp_payment(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method."}, status=405)

    email = (request.POST.get("email") or "").strip()
    aud_amount = (request.POST.get("aud_amount") or "").strip()
    send_customer_email = request.POST.get("send_email") == "on"

    if not aud_amount:
        return JsonResponse({"error": "AUD amount is required"}, status=400)

    try:
        aud_amount = Decimal(aud_amount)
    except:
        return JsonResponse({"error": "Invalid AUD amount"}, status=400)

    if aud_amount <= 0:
        return JsonResponse({"error": "AUD amount must be greater than 0"}, status=400)

    # 실시간 시세 조회
    xrp_price = None
    for attempt in range(3):
        try:
            res = requests.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=ripple&vs_currencies=aud",
                timeout=5,
            )
            res.raise_for_status()
            xrp_price = Decimal(res.json()["ripple"]["aud"])
            break
        except Exception as e:
            logger.warning("CoinGecko price fetch failed (attempt %s): %s", attempt + 1, e)

    if not xrp_price:
        xrp_price = Decimal("1.5")  # fallback

    xrp_amount = (aud_amount / xrp_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    dest_tag = email_to_tag(email or "no-email")

    # ✅ 관리자 알림: 이메일 유효성 무관하게 항상 발송
    internal_msg = (
        f"Customer Email (entered): {email or '(empty)'}\n"
        f"AUD Amount: {aud_amount}\n"
        f"XRP Amount: {xrp_amount}\n"
        f"Destination Tag: {dest_tag}"
    )
    send_xrp_internal_email.delay(
        "New XRP Payment Request",
        internal_msg,
        RECIPIENT_EMAIL,
        [RECIPIENT_EMAIL],
    )

    # 이메일이 입력되어 있고 Post에 존재하면 고객 메일/DB 기록/JSON 반환
    email_sent = False
    if email and Post.objects.filter(email=email).exists():
        if send_customer_email:
            send_xrp_customer_email.delay(
                email,
                str(xrp_amount),
                XRP_ADDRESS,
                dest_tag,
            )
            email_sent = True

        XrpPayment.objects.create(
            email=email,
            aud_amount=aud_amount,
            xrp_amount=xrp_amount,
            dest_tag=dest_tag,
            email_sent=email_sent,
        )

        return JsonResponse({
            "xrp_amount": str(xrp_amount),
            "xrp_address": XRP_ADDRESS,
            "dest_tag": dest_tag,
        })

    # 이메일이 없거나 Post에 없는 경우: DB 기록 없이 오류 메시지
    return JsonResponse({"error": "Invalid email address"}, status=400)


def xrp_payment_page(request):
    return render(request, "basecamp/includes/xrp_payment.html")


# 오류 핸들러
def custom_bad_request(request, exception):
    return render(request, "400.html", status=400)

def custom_forbidden(request, exception):
    return render(request, "403.html", status=403)

def custom_page_not_found(request, exception):
    return render(request, "404.html", status=404)

def custom_server_error(request):
    return render(request, "500.html", status=500)

def custom_bad_gateway(request):
    return render(request, "502.html", status=502)

def custom_under_maintenance(request):
    return render(request, "503.html", status=503)