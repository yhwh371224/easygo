from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Post


@receiver(post_save, sender=Post)
def auto_generate_review_reply(sender, instance, created, **kwargs):
    """When a review is published and has no reply yet, generate one via Claude AI."""
    if instance.is_published and not instance.reply:
        try:
            from easygo_review.tasks import generate_review_reply
            generate_review_reply.delay(instance.pk)
        except Exception as e:
            print(f"[review_reply] Signal trigger failed for Post {instance.pk}: {e}")
