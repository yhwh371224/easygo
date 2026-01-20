from django.core.management.base import BaseCommand
from blog.models import Post, Inquiry
from datetime import timedelta
from django.utils import timezone


class Command(BaseCommand):
    help = "Delete cancelled records older than 1 month based on pickup_date from Post and Inquiry models."

    def handle(self, *args, **options):
        models_to_check = [Post, Inquiry]
        total_deleted = 0
        cutoff_date = timezone.now() - timedelta(days=14)  # 한 달 전 기준

        for model in models_to_check:
            fields = [field.name for field in model._meta.fields]

            if 'cancelled' in fields and 'pickup_date' in fields:
                deleted, _ = model.objects.filter(cancelled=True, pickup_date__lt=cutoff_date).delete()
                if deleted > 0:
                    self.stdout.write(f"{model.__name__}: Deleted {deleted} cancelled records older than {cutoff_date.date()}.")
                    total_deleted += deleted
                else:
                    self.stdout.write(f"{model.__name__}: No cancelled records older than {cutoff_date.date()} to delete.")
            else:
                self.stdout.write(f"{model.__name__}: Missing 'cancelled' or 'pickup_date' field. Skipping.")

        self.stdout.write(self.style.SUCCESS(f"Finished. Total deleted: {total_deleted} records."))




