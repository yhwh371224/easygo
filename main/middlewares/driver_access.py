from django.shortcuts import redirect


class DriverAccessRestrictionMiddleware:
    """드라이버 계정은 /driver/ 대시보드 외 페이지에 접근할 수 없도록 제한"""

    ALLOWED_PREFIXES = ('/driver/', '/static/', '/media/', '/favicon.ico')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)

        if (user is not None and user.is_authenticated
                and not user.is_staff and not user.is_superuser
                and hasattr(user, 'driver')
                and not request.path.startswith(self.ALLOWED_PREFIXES)):
            return redirect('blog:driver_dashboard')

        return self.get_response(request)
