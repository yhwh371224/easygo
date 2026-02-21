from django.contrib.auth.backends import BaseBackend
from .models import Post


class PostEmailBackend(BaseBackend):
    def authenticate(self, request, email=None, **kwargs):
        try:
            post = Post.objects.get(email=email)
            return post
        except Post.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return Post.objects.get(pk=user_id)
        except Post.DoesNotExist:
            return 
            