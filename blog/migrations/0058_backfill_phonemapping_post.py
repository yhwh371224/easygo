from django.db import migrations


def backfill_post(apps, schema_editor):
    """
    0057 added PhoneMapping.post but couldn't populate it retroactively — any
    row created before that migration ran lands here with post=NULL. Without
    this, get_proxy_number() (now keyed on post, not from_number) would show
    no proxy number — and dashboard.html falls back to the customer's real
    contact — for every booking with an already-open session at deploy time,
    until something re-saves that Post.

    Best-effort match on the fields the row already carries; ambiguous or
    unmatched rows are left as-is rather than guessed.
    """

    PhoneMapping = apps.get_model('blog', 'PhoneMapping')
    Post = apps.get_model('blog', 'Post')

    for mapping in PhoneMapping.objects.filter(post__isnull=True):
        candidates = Post.objects.filter(
            driver__driver_name=mapping.driver_name,
            pickup_date=mapping.pickup_date,
            pickup_time=mapping.pickup_time,
            use_proxy=True,
            cancelled=False,
        )
        matches = list(candidates[:2])
        if len(matches) == 1:
            mapping.post = matches[0]
            mapping.save(update_fields=['post'])


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0057_phonemapping_post_fk'),
    ]

    operations = [
        migrations.RunPython(backfill_post, migrations.RunPython.noop),
    ]
