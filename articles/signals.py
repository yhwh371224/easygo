from django.core.files.base import ContentFile
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Post


@receiver(pre_save, sender=Post)
def capture_previous_status(sender, instance, **kwargs):
    instance._previous_status = None
    if not instance.pk:
        return
    previous = Post.objects.only("status").filter(pk=instance.pk).first()
    if previous:
        instance._previous_status = previous.status


@receiver(post_save, sender=Post)
def regenerate_sitemap_on_publish(sender, instance, **kwargs):
    """Regenerate sitemap on first publish."""
    if instance.was_just_published():
        try:
            from django.core.management import call_command
            call_command('generate_sitemap')
        except Exception as e:
            print(f"Sitemap generation failed: {e}")


@receiver(post_save, sender=Post)
def auto_fetch_thumbnail(sender, instance, created, **kwargs):
    """Automatically fetch and save a thumbnail from Unsplash if not set."""
    if instance.thumbnail:
        return

    if not instance.thumbnail_query:
        print(f"Unsplash: no thumbnail_query set for '{instance.title}'")
        return

    try:
        from posting_agent.image_ai import generate_post_image
        category_name = instance.category.name if instance.category else None
        result = generate_post_image(
            alt_text=instance.title,
            filename_slug=instance.slug,
            query=instance.thumbnail_query,
            category=category_name,
        )

        post = Post.objects.get(pk=instance.pk)
        post.thumbnail.save(result['filename'], ContentFile(result['image_bytes']), save=False)
        Post.objects.filter(pk=instance.pk).update(
            thumbnail=post.thumbnail.name,
            thumbnail_source_url=result['source_url'],
        )
        print(f"Unsplash thumbnail saved: {result['filename']}")

    except Exception as e:
        print(f"Unsplash thumbnail fetch failed: {e}")


@receiver(post_save, sender=Post)
def trigger_gmb_posting(sender, instance, created, **kwargs):
    """Trigger GMB posting on first publish if not yet posted to Google."""
    if instance.was_just_published() and not instance.posted_to_google:
        try:
            from posting_agent.tasks import post_to_gmb_from_article
            post_to_gmb_from_article.delay(instance.pk)
        except Exception as e:
            print(f"GMB posting trigger failed: {e}")