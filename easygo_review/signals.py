from django.dispatch import receiver
from blog.models import Post
from allauth.socialaccount.models import SocialLogin
from allauth.account.signals import user_logged_in


@receiver(user_logged_in)
def link_post_to_user(sender, request, user, **kwargs):
    try:
        post = Post.objects.get(email=user.email)
        # Post와 User 연결 로직
    except Post.DoesNotExist:
        pass