# main/middlewares/cloudflare.py
class CloudflareMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        cf_ip = request.META.get('HTTP_CF_CONNECTING_IP')
        if cf_ip:
            request.META['REMOTE_ADDR'] = cf_ip
        return self.get_response(request)