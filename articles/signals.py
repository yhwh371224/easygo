import io
import json
import urllib.parse
import urllib.request

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from PIL import Image
from django.core.files.base import ContentFile

from .models import Post


@receiver(post_save, sender=Post)
def regenerate_sitemap_on_publish(sender, instance, **kwargs):
    """Regenerate sitemap whenever a post is saved with published status."""
    if instance.status == 'published':
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
        query = urllib.parse.quote(instance.thumbnail_query)
        api_url = (
            f"https://api.unsplash.com/search/photos"
            f"?query={query}&per_page=1&orientation=landscape"
            f"&client_id={settings.UNSPLASH_ACCESS_KEY}"
        )

        with urllib.request.urlopen(api_url, timeout=10) as response:
            data = json.loads(response.read())

        results = data.get('results', [])
        if not results:
            print(f"Unsplash: no results for '{instance.thumbnail_query}'")
            return

        image_url = results[0]['urls']['regular']
        with urllib.request.urlopen(image_url, timeout=10) as img_response:
            img_data = img_response.read()

        img = Image.open(io.BytesIO(img_data)).convert('RGB')
        buffer = io.BytesIO()
        img.save(buffer, format='WEBP', quality=85)
        buffer.seek(0)

        filename = f"{instance.slug}.webp"
        post = Post.objects.get(pk=instance.pk)
        post.thumbnail.save(filename, ContentFile(buffer.getvalue()), save=False)
        Post.objects.filter(pk=instance.pk).update(thumbnail=post.thumbnail.name, thumbnail_source_url=image_url)
        print(f"Unsplash thumbnail saved: {filename}")

    except Exception as e:
        print(f"Unsplash thumbnail fetch failed: {e}")


@receiver(post_save, sender=Post)
def trigger_gmb_posting(sender, instance, created, **kwargs):
    """Trigger GMB posting when a post is published and not yet posted to Google."""
    if instance.status == 'published' and not instance.posted_to_google:
        try:
            from posting_agent.tasks import post_to_gmb_from_article
            post_to_gmb_from_article.delay(instance.pk)
        except Exception as e:
            print(f"GMB posting trigger failed: {e}")