from django.utils.deprecation import MiddlewareMixin
from .models import Region


class RegionMiddleware(MiddlewareMixin):
    """
    URL의 첫 번째 세그먼트가 활성화된 Region slug와 일치하면
    request.region에 Region 인스턴스를 주입한다.
    일치하지 않으면 request.region = None.
    """

    def process_request(self, request):
        request.region = None
        path_parts = request.path_info.strip('/').split('/')
        if not path_parts or not path_parts[0]:
            return

        slug = path_parts[0]
        try:
            request.region = Region.objects.get(slug=slug, is_active=True)
        except Region.DoesNotExist:
            pass
