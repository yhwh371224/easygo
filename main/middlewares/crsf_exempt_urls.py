# main/middlewares/csrf_exempt_urls.py 새 파일 생성
from django.middleware.csrf import CsrfViewMiddleware

class CsrfExemptMiddleware(CsrfViewMiddleware):
    EXEMPT_URLS = ['/gmail_webhook/']
    
    def process_view(self, request, callback, callback_args, callback_kwargs):
        if request.path in self.EXEMPT_URLS:
            return None
        return super().process_view(request, callback, callback_args, callback_kwargs)