from django.http import HttpResponseForbidden

class BlockIPMiddleware:
    BLOCKED_IPS = ['207.154.205.99']

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = request.META.get('REMOTE_ADDR')
        if ip in self.BLOCKED_IPS:
            return HttpResponseForbidden("Forbidden: Your IP address is blocked.")
        
        response = self.get_response(request)
        return response
