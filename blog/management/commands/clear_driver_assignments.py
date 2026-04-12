import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.models import Post
from utils.calendar_sync import delete_from_calendar

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Clear driver assignments for yesterday's posts and remove driver calendar events."

    def handle(self, *args, **options):
        yesterday = (timezone.now() - timedelta(days=1)).date()

        posts = Post.objects.filter(
            pickup_date=yesterday,
            driver__isnull=False,
        ).select_related('driver')

        total = posts.count()
        if total == 0:
            self.stdout.write(f"No driver-assigned posts found for {yesterday}.")
            logger.info(f"clear_driver_assignments: no posts for {yesterday}")
            return

        cleared = 0
        for post in posts:
            driver = post.driver
            driver_name = driver.driver_name if driver else None

            # notice 필드에 드라이버 이름 기록
            if driver_name:
                if post.notice:
                    post.notice = f"{post.notice} | {driver_name}"
                else:
                    post.notice = driver_name

            # 드라이버 캘린더 이벤트 삭제
            if post.driver_calendar_event_id and driver and driver.google_calendar_id:
                try:
                    delete_from_calendar(driver.google_calendar_id, post.driver_calendar_event_id)
                except Exception as e:
                    logger.error(
                        f"Failed to delete driver calendar event for post {post.id}: {e}"
                    )

            # 드라이버 초기화 — queryset.update()로 시그널 우회
            # post.save()를 쓰면 pre_save(reset_driver_calendar_event_id)가 이중 삭제를 시도하고
            # post_save(async_create_event_on_calendar)가 불필요한 Celery 태스크를 발행한다.
            Post.objects.filter(pk=post.pk).update(
                notice=post.notice,
                driver=None,
                driver_calendar_event_id=None,
            )
            cleared += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Cleared {cleared}/{total} driver assignments for {yesterday}."
            )
        )
        logger.info(f"clear_driver_assignments: cleared {cleared}/{total} posts for {yesterday}")
