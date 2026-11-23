import io
import shutil
import tempfile
from unittest import mock

from django.test import TestCase, override_settings
from PIL import Image

from articles.models import Post
from posting_agent import tasks


def _webp_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (20, 10), (255, 200, 0)).save(buf, "WEBP")
    return buf.getvalue()


class _Resp:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass


class PostToGmbTests(TestCase):
    """GBP 게시: webp 사진은 JPG 로 바꿔 올리고, 실패하면 텔레그램으로 알린다.
    외부 호출(GBP API, 사진 다운로드, 텔레그램)은 전부 mock — status 는 draft 로만 만들어
    publish 신호(실제 GBP 게시)가 절대 타지 않게 한다."""

    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=self.media)
        override.enable()
        self.addCleanup(override.disable)
        self.post = Post.objects.create(
            title="T2 guide", slug="t2-guide", content="<p>x</p>", status="draft",
            gmb_content="Hello GBP",
            thumbnail_source_url="https://easygo.s3.ap-southeast-2.amazonaws.com/photo.webp",
        )

    @mock.patch("posting_agent.tasks._alert_staff")
    @mock.patch("posting_agent.gmb_poster.post_to_google_business", return_value=(True, ""))
    @mock.patch("posting_agent.tasks.requests.get", return_value=_Resp(_webp_bytes()))
    def test_webp_is_converted_to_jpg(self, _get, gbp, alert):
        tasks.post_to_gmb_from_article(self.post.pk)

        image_url = gbp.call_args.kwargs["image_url"]
        self.assertTrue(image_url.startswith("https://easygoshuttle.com.au/media/articles/gmb/t2-guide"))
        self.assertTrue(image_url.endswith(".jpg"))
        with open(f"{self.media}/articles/gmb/t2-guide.jpg", "rb") as f:
            self.assertEqual(Image.open(f).format, "JPEG")
        self.post.refresh_from_db()
        self.assertTrue(self.post.posted_to_google)
        alert.assert_not_called()

    @mock.patch("posting_agent.tasks._alert_staff")
    @mock.patch("posting_agent.gmb_poster.post_to_google_business", return_value=(True, ""))
    @mock.patch("posting_agent.tasks.requests.get")
    def test_jpg_url_is_used_as_is(self, get, gbp, alert):
        url = "https://images.unsplash.com/photo-1?fm=jpg&q=80"
        Post.objects.filter(pk=self.post.pk).update(thumbnail_source_url=url)

        tasks.post_to_gmb_from_article(self.post.pk)

        self.assertEqual(gbp.call_args.kwargs["image_url"], url)
        get.assert_not_called()
        alert.assert_not_called()

    @mock.patch("posting_agent.tasks._alert_staff")
    @mock.patch("posting_agent.gmb_poster.post_to_google_business",
                return_value=(False, '400 {"error": "INVALID_ARGUMENT"}'))
    @mock.patch("posting_agent.tasks.requests.get", return_value=_Resp(_webp_bytes()))
    def test_api_failure_alerts_staff(self, _get, _gbp, alert):
        tasks.post_to_gmb_from_article(self.post.pk)

        self.post.refresh_from_db()
        self.assertFalse(self.post.posted_to_google)
        alert.assert_called_once()
        msg = alert.call_args.args[0]
        self.assertIn("GBP 게시 실패", msg)
        self.assertIn("INVALID_ARGUMENT", msg)
        self.assertIn(f"#{self.post.pk}", msg)

    @mock.patch("posting_agent.tasks._alert_staff")
    @mock.patch("posting_agent.gmb_poster.post_to_google_business", side_effect=RuntimeError("token expired"))
    @mock.patch("posting_agent.tasks.requests.get", return_value=_Resp(_webp_bytes()))
    def test_exception_alerts_staff(self, _get, _gbp, alert):
        tasks.post_to_gmb_from_article(self.post.pk)

        self.post.refresh_from_db()
        self.assertFalse(self.post.posted_to_google)
        self.assertIn("token expired", alert.call_args.args[0])

    @mock.patch("posting_agent.tasks._alert_staff")
    @mock.patch("posting_agent.gmb_poster.post_to_google_business", return_value=(True, ""))
    @mock.patch("posting_agent.tasks.requests.get", return_value=_Resp(b"not an image"))
    def test_conversion_failure_posts_without_photo_and_alerts(self, _get, gbp, alert):
        tasks.post_to_gmb_from_article(self.post.pk)

        self.assertIsNone(gbp.call_args.kwargs["image_url"])
        self.assertIn("JPG 변환 실패", alert.call_args.args[0])
        self.post.refresh_from_db()
        self.assertTrue(self.post.posted_to_google)
