from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Post


@receiver(post_save, sender=Post)
def regenerate_sitemap_on_publish(sender, instance, **kwargs):
    if instance.status == 'published':
        try:
            from django.core.management import call_command
            call_command('generate_sitemap')
        except Exception as e:
            print(f"Sitemap generation failed: {e}")