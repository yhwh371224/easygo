from django.core.management.base import BaseCommand
from blog.models import Post, Inquiry


class Command(BaseCommand):
    help = "Delete records with cancelled=True from Post and Inquiry models only."

    def handle(self, *args, **options):
        models_to_check = [Post, Inquiry]
        total_deleted = 0

        for model in models_to_check:
            if 'cancelled' in [field.name for field in model._meta.fields]:
                deleted, _ = model.objects.filter(cancelled=True).delete()
                if deleted > 0:
                    self.stdout.write(f"{model.__name__}: Deleted {deleted} cancelled records.")
                    total_deleted += deleted
                else:
                    self.stdout.write(f"{model.__name__}: No cancelled records to delete.")
            else:
                self.stdout.write(f"{model.__name__}: No 'cancelled' field. Skipping.")

        self.stdout.write(self.style.SUCCESS(f"Finished. Total deleted: {total_deleted} records."))



