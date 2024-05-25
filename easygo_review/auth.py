from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from blog.models import Post


class PostEmailAuthBackend(BaseBackend):
    def authenticate(self, request, email=None):
        UserModel = get_user_model()
        try:            
            post = Post.objects.get(email=email).first()
            if post:            
                user, created = UserModel.objects.get_or_create(email=email)
                return user
            return None
        except Post.DoesNotExist:
            return None

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None 
        

