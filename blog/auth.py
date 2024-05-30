from django.contrib.auth.backends import ModelBackend
from blog.models import Post

class EmailAuthBackend(ModelBackend):
    def authenticate(self, request, email=None, **kwargs):
        try:
            user = Post.objects.get(email=email)
            return user
        except Post.DoesNotExist:
            return None