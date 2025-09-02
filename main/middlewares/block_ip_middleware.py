import os
import time
from django.http import HttpResponseForbidden
from django.conf import settings


class BlockIPEmailMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

        # 설정에서 파일 경로 불러오기
        self.blocked_ips_file = getattr(settings, "BLOCKED_IP_FILE", "/etc/django/blocked_ips.txt")
        self.blocked_emails_file = getattr(settings, "BLOCKED_EMAIL_FILE", "/etc/django/blocked_emails.txt")

        self._blocked_ips = set()
        self._blocked_emails = set()
        self._last_load_time = 0
        self._cache_timeout = 86400  # 하루에 한 번 reload

        self.load_blocked_lists()

    def __call__(self, request):
        # Admin 페이지 제외
        if request.path.startswith('/admin/'):
            return self.get_response(request)
        
        ip = self.get_client_ip(request)
        email = self.get_email_from_request(request)

        # IP 차단
        if ip in self._blocked_ips:
            return HttpResponseForbidden("Forbidden: Your IP address is blocked.")

        # 이메일 차단
        if email and email.lower() in self._blocked_emails:
            return HttpResponseForbidden("Forbidden: This email is blocked.")

        return self.get_response(request)

    def load_blocked_lists(self):
        """IP와 이메일 파일을 동시에 읽어서 메모리 갱신"""
        self._blocked_ips = self.load_file(self.blocked_ips_file)
        self._blocked_emails = {x.lower() for x in self.load_file(self.blocked_emails_file)}
        self._last_load_time = time.time()

    def load_file(self, path):
        """파일에서 한 줄씩 읽어서 set 반환"""
        if os.path.exists(path):
            with open(path, "r") as f:
                return {line.strip() for line in f if line.strip() and not line.startswith("#")}
        return set()

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        return x_forwarded_for.split(",")[0].strip() if x_forwarded_for else request.META.get("REMOTE_ADDR")

    def get_email_from_request(self, request):
        if request.method == "POST":
            return request.POST.get("email")
        return None
