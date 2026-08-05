from django.db import migrations


def forwards(apps, schema_editor):
    Post = apps.get_model('articles', 'Post')
    Region = apps.get_model('regions', 'Region')

    sydney = Region.objects.filter(slug='sydney').first()

    for post in Post.objects.all():
        if post.region_id:
            post.regions.add(post.region_id)
        elif sydney:
            # 기존 동작 보존: region 미지정 글은 시드니에서만 노출되고 있었으므로
            # 그 동작을 그대로 유지한다. 새로 만드는 "범용 글"(모든 지역 노출)은
            # 이 마이그레이션 이후 admin에서 Regions를 비워둘 때만 해당된다.
            post.regions.add(sydney.id)


def backwards(apps, schema_editor):
    Post = apps.get_model('articles', 'Post')
    for post in Post.objects.all():
        first_region = post.regions.first()
        if first_region:
            post.region_id = first_region.id
            post.save(update_fields=['region'])
        post.regions.clear()


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0006_post_add_regions_m2m'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
