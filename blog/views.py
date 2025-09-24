import requests
import logging
from django.shortcuts import render
from decimal import Decimal, ROUND_HALF_UP
from .models import XrpPayment
import hashlib, qrcode, base64
from io import BytesIO
from .tasks import send_xrp_internal_email, send_xrp_customer_email

logger = logging.getLogger(__name__)

XRP_ADDRESS = "r9WZsBV3fhdHgXEkiJwGUDdgQJztGkYRGB"

def email_to_tag(email: str) -> int:
    """이메일 기반 32비트 Destination Tag 생성"""
    hash_int = int(hashlib.md5(email.encode()).hexdigest(), 16)
    return hash_int % (2**32)

def xrp_payment(request):
    result = None

    if request.method == "POST":
        email = request.POST.get("email")
        aud_amount = request.POST.get("aud_amount")
        send_customer_email = request.POST.get("send_email") == "on"

        try:
            aud_amount = Decimal(aud_amount)
        except:
            aud_amount = None

        if email and aud_amount and aud_amount > 0:
            # 실시간 XRP/AUD 시세 with retry
            xrp_price = None
            for attempt in range(3):
                try:
                    res = requests.get(
                        "https://api.coingecko.com/api/v3/simple/price?ids=ripple&vs_currencies=aud",
                        timeout=5
                    )
                    res.raise_for_status()
                    xrp_price = Decimal(res.json()["ripple"]["aud"])
                    break
                except Exception as e:
                    logger.warning("CoinGecko price fetch failed (attempt %s): %s", attempt + 1, e)
            if not xrp_price:
                xrp_price = Decimal("1.5")  # fallback 시세

            # 2자리 반올림
            xrp_amount = (aud_amount / xrp_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            dest_tag = email_to_tag(email)

            # QR 코드
            qr_uri = f"xrp:{XRP_ADDRESS}?dt={dest_tag}&amount={xrp_amount}"
            qr = qrcode.QRCode(box_size=8, border=2)
            qr.add_data(qr_uri)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            result = {
                "xrp_amount": xrp_amount,
                "xrp_address": XRP_ADDRESS,
                "dest_tag": dest_tag,
                "email": email,
                "aud_amount": aud_amount,
                "qr_base64": qr_base64
            }

            # 내부 알림 메일 (Celery)
            internal_msg = (
                f"Customer Email: {email}\n"
                f"AUD Amount: {aud_amount}\n"
                f"XRP Amount: {xrp_amount}\n"
                f"Destination Tag: {dest_tag}"
            )
            send_xrp_internal_email.delay(
                "New XRP Payment Request",
                internal_msg,
                "no-reply@yourcompany.com",
                ["yourcompany@company.com"],
            )

            # 고객 메일 (옵션) — Celery task uses its own HTML template
            email_sent = False
            if send_customer_email:
                send_xrp_customer_email.delay(
                    email,
                    str(xrp_amount),   # 문자열로 전달 (Decimal 처리 tasks.py에서)
                    XRP_ADDRESS,
                    dest_tag
                )
                email_sent = True

            # DB 기록
            XrpPayment.objects.create(
                email=email,
                aud_amount=aud_amount,
                xrp_amount=xrp_amount,
                dest_tag=dest_tag,
                email_sent=email_sent
            )

    return render(request, "basecamp/includes/xrp_payment.html", {"result": result})


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
