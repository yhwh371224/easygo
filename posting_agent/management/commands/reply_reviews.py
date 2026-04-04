import asyncio
from django.core.management.base import BaseCommand
from posting_agent.review_manager import get_unanswered_reviews, generate_reply
from posting_agent.telegram_bot import send_review_for_approval


class Command(BaseCommand):
    help = 'Fetch unanswered reviews and send to Telegram for approval'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max',
            type=int,
            default=10,
            help='Max number of reviews to process (default: 10)',
        )

    def handle(self, *args, **options):
        max_reviews = options['max']

        self.stdout.write("📋 미답변 리뷰 가져오는 중...")
        reviews = get_unanswered_reviews(max_reviews=max_reviews)

        if not reviews:
            self.stdout.write(self.style.SUCCESS("✅ 미답변 리뷰가 없어요!"))
            return

        total = len(reviews)
        self.stdout.write(f"📝 미답변 리뷰 {total}개 발견!")

        for i, review in enumerate(reviews, 1):
            reviewer = review.get('reviewer', {}).get('displayName', '익명')
            self.stdout.write(f"✍️  [{i}/{total}] {reviewer} 리뷰 답변 생성 중...")

            reply = generate_reply(review)
            asyncio.run(send_review_for_approval(review, reply, i, total))

            self.stdout.write(f"📨 [{i}/{total}] Telegram 전송 완료!")

        self.stdout.write(self.style.SUCCESS(f"\n✅ {total}개 리뷰 Telegram으로 전송됐어요! 승인해주세요."))