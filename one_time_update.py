# one_time_update.py
from django.db.models import Q
from blog.models import Post


posts = Post.objects.filter(
    Q(paid=False) | Q(paid__isnull=True) | Q(paid=""),
).exclude(return_pickup_time="")

for post in posts:
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

        print(f"✔ Updated {post.email} - price set to {half_price}")
    except Exception as e:
        print(f"❌ Error on {getattr(post, 'email', 'unknown email')}: {e}")

