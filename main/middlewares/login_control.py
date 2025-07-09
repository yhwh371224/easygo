from django.conf import settings


class AccountLoginMethodMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 경로가 어드민(admin)일 경우 설정 비활성화
        if request.path.startswith('/horeb_yhwh/'):
            request.use_email_only_login = False
        else:
            request.use_email_only_login = True

        return self.get_response(request)
