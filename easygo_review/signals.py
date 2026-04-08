from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Post


@receiver(post_save, sender=Post)
def auto_generate_review_reply(sender, instance, created, **kwargs):
    """On new review creation, queue a Claude AI reply (saved as EasyGo Comment)."""
    if not created:
        return
    try:
        from easygo_review.tasks import generate_review_reply
        generate_review_reply.delay(instance.pk)
    except Exception as e:
        print(f"[review_reply] Signal trigger failed for Post {instance.pk}: {e}")
