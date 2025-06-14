from django.db.models import Q
from blog.models import Post


qs = Post.objects.filter(
    Q(paid__isnull=True) |
    Q(paid__exact="") |
    Q(paid__in=["0", "0.0", "0.00", "False"]),
    return_pickup_time__isnull=False
).exclude(return_pickup_time__exact="")

for index, post in enumerate(qs.iterator(), start=1):
    try:
        original_price = float(post.price or 0)
        half_price = round(original_price / 2, 2)

        original_notice = (post.notice or "").strip()

        new_info = f"Both trips: ${original_price:.2f}"
        if new_info not in original_notice:
            if original_notice:
                updated_notice = f"{original_notice} | {new_info}"
            else:
                updated_notice = new_info
        else:
            updated_notice = original_notice  

        post.price = half_price
        post.notice = updated_notice
        post.save(update_fields=["price", "notice"])

        if index % 100 == 0:
            print(f"✅ {index} posts updated...")

    except Exception as e:
        print(f"❌ Error on {getattr(post, 'email', 'unknown email')}: {e}")

