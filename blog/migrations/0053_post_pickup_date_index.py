from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):

    # CREATE INDEX CONCURRENTLY cannot run inside a transaction, so this
    # migration must be non-atomic. Builds the index without locking writes.
    atomic = False

    dependencies = [
        ('blog', '0052_post_discrepancy_final_sent_at_and_more'),
    ]

    operations = [
        AddIndexConcurrently(
            model_name='post',
            index=models.Index(fields=['pickup_date'], name='blog_post_pickup_date_idx'),
        ),
    ]
