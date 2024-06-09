from django.contrib.auth.backends import BaseBackend
from blog.models import Post 
from django.contrib.auth.models import User


class EmailBackend(BaseBackend):
    def authenticate(self, request, email=None):
        try:
            user = User.objects.get(email=email)
            return user
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
        
