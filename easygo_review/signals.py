from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Comment, Post


@receiver(post_save, sender=Post)
def auto_generate_review_reply(sender, instance, created, **kwargs):
    """When a review has no EasyGo reply comment yet, generate one via Claude AI."""
    from easygo_review.tasks import EASYGO_AUTHOR
    if not Comment.objects.filter(post=instance, author=EASYGO_AUTHOR).exists():
        try:
            from easygo_review.tasks import generate_review_reply
            generate_review_reply.delay(instance.pk)
        except Exception as e:
            print(f"[review_reply] Signal trigger failed for Post {instance.pk}: {e}")
