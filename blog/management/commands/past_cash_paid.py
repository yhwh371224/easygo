from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from blog.models import Post


class Command(BaseCommand):
    help = 'For past bookings with cash=True and paid is empty, fill paid with price'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()

        qs = Post.objects.filter(
            pickup_date__lt=today,
            cancelled=False,
            cash=True,
            paid__isnull=True,
        )

        updated_count = qs.update(paid=models.F('price'))

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {updated_count} records (paid = price)'
            )
        )
