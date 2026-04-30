from django.core.management.base import BaseCommand
from django.utils import timezone, timedelta
from django.db import models
from blog.models import Post


class Command(BaseCommand):
    help = 'For past bookings with cash=True and paid is empty, fill paid with price'

    def handle(self, *args, **kwargs):

        yesterday = timezone.now().date() - timedelta(days=1)

        qs = Post.objects.filter(
            pickup_date=yesterday,
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
