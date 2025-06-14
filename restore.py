from blog.models import Post
from django.db.models import Q
import re

qs = Post.objects.filter(
    Q(return_pickup_time__isnull=True) | Q(return_pickup_time__exact=""),
    notice__icontains="Both trips:"
)

for index, post in enumerate(qs.iterator(), start=1):
    try:
        # price 복원
        current_price = float(post.price or 0)
        restored_price = round(current_price * 2, 2)

        # notice에서 "Both trips: $..." 부분 제거
        notice = post.notice or ""
        updated_notice = re.sub(r'\|?\s*Both trips: \$\d+(?:\.\d{1,2})?', '', notice).strip(' |')

        # 필드 업데이트
        post.price = restored_price
        post.notice = updated_notice
        post.save(update_fields=["price", "notice"])

        print(f"🔁 Restored {post.email} - price set back to {restored_price}")

    except Exception as e:
        print(f"❌ Error on {getattr(post, 'email', 'unknown email')}: {e}")
