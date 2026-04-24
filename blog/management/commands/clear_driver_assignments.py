import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.models import Post
from utils.calendar_sync import delete_from_calendar

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Remove driver calendar events for yesterday's completed posts."

    def handle(self, *args, **options):
        yesterday = (timezone.now() - timedelta(days=1)).date()

        posts = Post.objects.filter(
            pickup_date=yesterday,
            driver__isnull=False,
            driver_calendar_event_id__isnull=False,  # 캘린더 이벤트 있는 것만
        ).select_related('driver')

        total = posts.count()
        if total == 0:
            logger.info(f"clear_driver_assignments: no posts for {yesterday}")
            return

        for post in posts:
            driver = post.driver
            if driver and driver.google_calendar_id:
                try:
                    delete_from_calendar(driver.google_calendar_id, post.driver_calendar_event_id)
                    Post.objects.filter(pk=post.pk).update(driver_calendar_event_id=None)
                    logger.info(f"Deleted calendar event for post {post.id}")
                except Exception as e:
                    logger.error(f"Failed to delete calendar event for post {post.id}: {e}")