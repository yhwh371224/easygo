from blog.models import Post
import re

qs = Post.objects.filter(notice__regex=r'Both trips: \$\d+(?:\.\d{2})? \| Both trips: \$\d+(?:\.\d{2})?')

for index, post in enumerate(qs.iterator(), start=1):
    try:
        # 현재 price 두 배로 복구
        current_price = float(post.price or 0)
        restored_price = round(current_price * 2, 2)

        # notice: "Both trips: $280.00 | Both trips: $140.00" → "Both trips: $280.00"
        notice = post.notice or ""
        both_matches = re.findall(r'Both trips: \$\d+(?:\.\d{2})?', notice)

        if both_matches:
            # 첫 번째만 유지
            updated_notice = re.sub(r'\s*\|\s*Both trips: \$\d+(?:\.\d{2})?', '', notice, count=1)

            post.price = restored_price
            post.notice = updated_notice.strip(" |")
            post.save(update_fields=["price", "notice"])

            print(f"🔁 Fixed {post.email} - price restored to {restored_price}")

    except Exception as e:
        print(f"❌ Error on {getattr(post, 'email', 'unknown email')}: {e}")

