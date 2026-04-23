import requests, logging
from decimal import ROUND_HALF_UP
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from main.settings import RECIPIENT_EMAIL
# from .models import XrpPayment, Post
# from .tasks import send_xrp_internal_email, send_xrp_customer_email


logger = logging.getLogger(__name__)

# XRP_ADDRESS = "r9WZsBV3fhdHgXEkiJwGUDdgQJztGkYRGB"

def email_to_tag(email: str) -> int:
    """이메일 기반 32비트 Destination Tag 생성"""
    import hashlib
    hash_int = int(hashlib.md5(email.encode()).hexdigest(), 16)
    return hash_int % (2**32)


# 공통 오류 핸들러
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
