from django.http import HttpResponseForbidden

class BlockIPMiddleware:
    BLOCKED_IPS = ['207.154.205.99', '147.78.47.81', '27.210.152.236', '157.66.54.6', '43.128.84.144']

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = request.META.get('REMOTE_ADDR')
        if ip in self.BLOCKED_IPS:
            return HttpResponseForbidden("Forbidden: Your IP address is blocked.")
        
        response = self.get_response(request)
        return response
