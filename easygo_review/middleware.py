from django.contrib.auth.models import AnonymousUser
from blog.models import Post

class PostAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        id = request.session.get('id')
        if id:
            try:
                request.user = Post.objects.get(id=id)
            except Post.DoesNotExist:
                request.user = AnonymousUser()
        else:
            request.user = AnonymousUser()
        response = self.get_response(request)
        return response