
# # python manage.py shell 
# from blog.models import Post
# Post.objects.filter(email="shontal.heeramun@australiaawardsafrica.org").update(email="sungkam718@gmail.com")
# Post.objects.filter(email="sungkam718@gmail.com").update(email="shontal.heeramun@australiaawardsafrica.org")
# Post.objects.filter(email="sungkam3@gmail.com").update(email="janice@scenetobelieve.com")
# Post.objects.filter(email="kate@diveplanit.com").update(email="sungkam3@gmail.com")
# Post.objects.filter(email="sungkam3@gmail.com").update(email="kate@diveplanit.com")

# Post.objects.filter(
#     email="kate@diveplanit.com",
#     pickup_date__year=2025
# ).update(email="sungkam3@gmail.com")

# Post.objects.filter(
#     pickup_date__year=2026
# ).update(paid=False)


# ---------------------------------------------------------------------------
# 실서버 데이터로 인보이스 발송 테스트하기 (2026-09-22)
#
# 위 방식(Post.email을 실제로 바꿨다가 되돌리기)은 되돌리는 걸 깜빡하면 그
# 예약의 실제 고객 이메일이 테스트 주소로 영구히 남는 위험이 있다. 아래
# 방식은 DB의 email 필드는 전혀 건드리지 않고, 인보이스를 만드는 실제 로직
# (_build_multi_context, _send_invoice_email)은 그대로 재사용하면서 메일
# 보내는 마지막 단계에서 recipient_list만 테스트 주소로 바꿔치기한다.
# 그래서 되돌릴 것 자체가 없다.
#
# 사용법: 실서버에서 `python manage.py shell` 진입 후 아래 붙여넣기.
# email/from_date/to_date/TEST_RECIPIENT만 바꿔서 쓰면 됨.
#
# from datetime import date
# from django.conf import settings
# from blog.models import Post
# from basecamp.views.payments import (
#     _resolve_inv_no, _resolve_bookings, _build_multi_context, _send_invoice_email,
# )
#
# TEST_RECIPIENT = "sungkam3@gmail.com"   # 실제로 메일 받을 주소
#
# email = "janice@scenetobelieve.com"     # 조회할 고객 (실제 이메일은 안 바뀜)
# from_date = "2026-09-27"
# to_date = "2026-10-02"
#
# params = {
#     'email': email, 'apply_gst_flag': None, 'surcharge_input': None,
#     'discount_input': None, 'inv_no': None, 'toll_input': None,
#     'index': '1', 'from_date': from_date, 'to_date': to_date,
#     'deposit_percent_input': None,
# }
#
# users = (Post.objects.filter(booker_email__iexact=email) |
#          Post.objects.filter(email__iexact=email)).distinct()
#
# user = users[0]
# today = date.today()
# inv_no = _resolve_inv_no(user, params['inv_no'])
# DEFAULT_BANK = getattr(settings, "DEFAULT_BANK_CODE", "westpac")
#
# bookings, multiple = _resolve_bookings(users, 0, from_date, to_date)
# template_name, context = _build_multi_context(bookings, params, inv_no, today, DEFAULT_BANK)
#
# # 핵심: 실제 뷰(invoice_detail)는 customer_recipients + [RECIPIENT_EMAIL]을
# # 넘기지만, 여기선 그 자리에 [TEST_RECIPIENT]만 넣어서 실제 고객·내부 주소로는
# # 전혀 안 나가고 테스트 주소로만 발송된다.
# _send_invoice_email(template_name, context, [TEST_RECIPIENT], inv_no)

