"""왜 이 예약에 잔액이 남아 있는지 한 줄 한 줄 분해해서 보여준다.

`paid` 만 고쳤는데도 잔액이 0 이 안 되는 경우(총액은 price 가 아니라
price + surcharge − discount 라서)를 눈으로 확인하려고 만들었다. 읽기 전용.

    python manage.py why_balance --email someone@example.com
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.blog_utils import _net_adjustment, booking_balance
from blog.models import Post


class Command(BaseCommand):
    help = "예약의 잔액을 price/surcharge/discount/paid 로 분해해 출력한다 (읽기 전용)"

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True)
        parser.add_argument(
            '--all-dates', action='store_true',
            help='기본은 오늘 이후 픽업만 — email dispatch 의 배분 대상과 동일하게 맞춘다',
        )

    def handle(self, *args, **options):
        email = options['email'].strip()

        qs = Post.objects.filter(email__iexact=email)
        if not options['all_dates']:
            qs = qs.filter(pickup_date__gte=timezone.localdate())
        bookings = list(qs.order_by('pickup_date'))

        # email dispatch 는 booker_email 이 있으면 그 값으로 email 컬럼을 뒤진다
        # (admin_ops.py:554) — 그래서 여행사 예약은 0 건이 나온다. 같이 보여준다.
        booker_hits = Post.objects.filter(booker_email__iexact=email).count()

        self.stdout.write(f"email={email}  matched={len(bookings)}  "
                          f"(booker_email 로 잡히는 예약: {booker_hits}건)")
        if not bookings:
            self.stdout.write(self.style.WARNING(
                "  → email 컬럼 기준으로 0건. email dispatch 의 Gratitude 배분도 "
                "0건이 되어 입금이 어디에도 반영되지 않는다."))
            return

        grand_due = 0.0
        for b in bookings:
            surcharge, discount = _net_adjustment(b)
            amounts = booking_balance(b)

            self.stdout.write("")
            self.stdout.write(
                f"  pk={b.pk}  {b.pickup_date}  "
                f"return_pickup_time={b.return_pickup_time!r}  "
                f"return_pickup_date={b.return_pickup_date}  cancelled={b.cancelled}"
            )
            self.stdout.write(
                f"    raw:  price={b.price!r}  paid={b.paid!r}  "
                f"surcharge={b.surcharge!r}  discount={b.discount!r}  toll={b.toll!r}"
            )

            if amounts is None:
                self.stdout.write(self.style.WARNING(
                    "    → price/paid 가 숫자가 아니라 금액 판정 불가 (배분·독촉에서 제외됨)"))
                continue

            total, paid, due = amounts
            self.stdout.write(
                f"    calc: total = price {float(b.price or 0):.2f} "
                f"+ surcharge {surcharge:.2f} - discount {discount:.2f} = {total:.2f}"
            )
            self.stdout.write(f"          due   = {total:.2f} - paid {paid:.2f} = {due:.2f}")

            if due > 0:
                grand_due += due
                if surcharge and abs(due - surcharge) < 0.005:
                    self.stdout.write(self.style.WARNING(
                        f"    → 잔액 {due:.2f} 가 surcharge {surcharge:.2f} 와 일치한다. "
                        f"paid 를 price 와 같게 맞춰도 surcharge 만큼 남는다."))

            if b.notice and '===' in b.notice:
                self.stdout.write(f"    notice: {b.notice.strip()}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"  합계 미납: ${round(grand_due, 2):.2f}"))

        # 왕복은 두 줄로 쪼개져 있는데 surcharge/discount 는 halve 되지 않고 양쪽에
        # 그대로 복사된다 (utils/return_booking.py). 청구서는 왕복 총액에 surcharge 를
        # 한 번만 얹으므로(basecamp/views/payments.py:323) 그 차액만큼 영구히 남는다.
        legs = [b for b in bookings if b.return_pickup_time]
        if len(legs) >= 2:
            sur_sum = sum(_net_adjustment(b)[0] for b in legs)
            if sur_sum:
                self.stdout.write(self.style.WARNING(
                    f"  ⚠️ 왕복 {len(legs)}줄에 surcharge 가 합계 ${sur_sum:.2f} 붙어 있다. "
                    f"청구서는 왕복 총액에 surcharge 를 한 번만 얹으므로, 손님이 청구서대로 "
                    f"완납해도 여기서는 약 ${sur_sum / 2:.2f} 가 미납으로 남는다."))

        # 왕복 짝 맞추기 — email dispatch 가 두 날짜를 찾을 때 쓰는 조건과 동일하다.
        # 날짜가 맞물리지 않으면 손님 메일에 날짜가 하나만 나간다.
        self.stdout.write("")
        self.stdout.write("  --- 왕복 짝 ---")
        paired = set()
        for b in bookings:
            if b.pk in paired or not b.return_pickup_date:
                continue
            mate = next((o for o in bookings
                         if o.pk != b.pk and o.pickup_date == b.return_pickup_date), None)
            if mate is None:
                self.stdout.write(self.style.WARNING(
                    f"  pk={b.pk} ({b.pickup_date}) 의 짝을 못 찾음 "
                    f"— return_pickup_date={b.return_pickup_date}"))
                continue
            paired.update({b.pk, mate.pk})
            swap_ok = mate.return_pickup_date == b.pickup_date
            self.stdout.write(
                f"  pk={b.pk} ({b.pickup_date}) ↔ pk={mate.pk} ({mate.pickup_date})"
                f"   날짜 맞교환={'OK' if swap_ok else '깨짐'}"
            )
            for tag, one, two in (('===RETURN===', b, mate),):
                def _seg(post):
                    for part in (post.notice or '').split('|'):
                        if tag in part:
                            return part.strip()
                    return None
                s1, s2 = _seg(one), _seg(two)
                if s1 and s2 and s1 != s2:
                    self.stdout.write(self.style.WARNING(
                        f"    ⚠️ 두 줄의 {tag} 기록이 다르다 — 같은 분할에서 나왔다면 같아야 한다:\n"
                        f"       pk={one.pk}: {s1}\n"
                        f"       pk={two.pk}: {s2}"))
