from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import models


class Command(BaseCommand):
    help = "Delete records with cancelled=True from all blog models that have a cancelled field."

    def handle(self, *args, **options):
        blog_models = apps.get_app_config('blog').get_models()
        total_deleted = 0

        for model in blog_models:
            if 'cancelled' in [field.name for field in model._meta.get_fields()]:
                deleted, _ = model.objects.filter(cancelled=True).delete()
                if deleted > 0:
                    self.stdout.write(f"{model.__name__}: Deleted {deleted} cancelled records.")
                    total_deleted += deleted
                else:
                    self.stdout.write(f"{model.__name__}: No cancelled records to delete.")
            else:
                self.stdout.write(f"{model.__name__}: No 'cancelled' field. Skipping.")

        self.stdout.write(self.style.SUCCESS(f"Finished. Total deleted: {total_deleted} records."))


