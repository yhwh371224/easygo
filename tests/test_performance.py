"""
Performance regression tests for DB optimisations (2026-03-09).

Covers:
  1+6. Sam driver cache            — get_default_driver()
  2.   QuerySet duplicate removal  — list(qs[:2]) pattern
  3.   select_related('driver')    — no N+1 on FK access
  4.   Q() unification             — single query for email | email1
  5.   bulk_update                 — O(1) queries regardless of row count
  8.   is_duplicate_submission()   — cache-flag instead of DB query

All tests override CACHES to LocMemCache so Redis is not required.
"""

import time
from datetime import date

from django.core.cache import cache
from django.db.models import Q
from django.test import TestCase, override_settings

from blog.models import Driver, Inquiry, Post
from basecamp.modules.view_helpers import is_duplicate_submission
from utils.booking_helper import get_default_driver


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

LOCMEM_CACHE = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}


def _make_post(email, *, name="Test User", price="100", paid="0", **kwargs):
    """Create a minimal Post fixture."""
    return Post.objects.create(
        name=name,
        email=email,
        no_of_passenger="1",
        pickup_date=date.today(),
        price=price,
        paid=paid,
        **kwargs,
    )


def _make_driver(name="Sam", **kwargs):
    defaults = dict(
        driver_contact="0400000000",
        driver_plate="ABC123",
        driver_car="Toyota Camry",
    )
    defaults.update(kwargs)
    return Driver.objects.create(driver_name=name, **defaults)


# ===========================================================================
# 1+6. Sam 드라이버 캐시
# ===========================================================================

@override_settings(CACHES=LOCMEM_CACHE)
class SamDriverCacheTest(TestCase):
    """get_default_driver() 는 첫 호출만 DB를 조회하고 이후는 캐시를 사용해야 한다."""

    def setUp(self):
        self.driver = _make_driver("Sam")
        cache.clear()

    def tearDown(self):
        cache.clear()

    # ------------------------------------------------------------------
    def test_first_call_hits_db_exactly_once(self):
        """첫 번째 호출은 DB 쿼리 1번만 실행되어야 한다."""
        with self.assertNumQueries(1):
            driver = get_default_driver()
        self.assertEqual(driver.driver_name, "Sam")

    def test_second_call_is_cache_hit_zero_queries(self):
        """캐시 워밍 후 두 번째 호출은 DB 쿼리 0번이어야 한다."""
        get_default_driver()  # warm cache
        with self.assertNumQueries(0):
            driver = get_default_driver()
        self.assertEqual(driver.driver_name, "Sam")

    def test_multiple_calls_stay_at_zero_queries(self):
        """캐시가 살아있는 동안 반복 호출은 모두 DB 쿼리 0번이어야 한다."""
        get_default_driver()  # warm
        with self.assertNumQueries(0):
            for _ in range(5):
                get_default_driver()

    def test_cache_clear_triggers_db_again(self):
        """캐시 초기화 후 재호출 시 DB 쿼리가 1번 다시 실행되어야 한다."""
        get_default_driver()  # warm
        cache.clear()         # simulate eviction
        with self.assertNumQueries(1):
            driver = get_default_driver()
        self.assertEqual(driver.driver_name, "Sam")

    def test_returned_object_has_correct_fields(self):
        """반환된 Driver 객체가 DB의 실제 데이터와 일치해야 한다."""
        driver = get_default_driver()
        self.assertEqual(driver.driver_name, self.driver.driver_name)
        self.assertEqual(driver.driver_contact, self.driver.driver_contact)
        self.assertEqual(driver.driver_plate, self.driver.driver_plate)


# ===========================================================================
# 2. QuerySet 중복 조회 제거
# ===========================================================================

@override_settings(CACHES=LOCMEM_CACHE)
class QuerysetSliceTest(TestCase):
    """list(Post.objects.filter(...)[:2]) 패턴이 쿼리 1번으로 두 객체를 반환해야 한다."""

    EMAIL = "slice@example.com"

    def setUp(self):
        # Post.Meta.ordering = ['-created'] → 나중에 생성된 것이 users[0]
        self.post_first  = _make_post(self.EMAIL, name="First Booking",  price="80")
        self.post_second = _make_post(self.EMAIL, name="Second Booking", price="120")

    # ------------------------------------------------------------------
    def test_slice_issues_single_db_query(self):
        """[:2] 슬라이스 후 list() 변환은 DB 쿼리 1번만 실행되어야 한다."""
        with self.assertNumQueries(1):
            users = list(Post.objects.filter(email__iexact=self.EMAIL)[:2])
        self.assertEqual(len(users), 2)

    def test_index_access_on_list_causes_no_extra_queries(self):
        """list로 변환 후 인덱스 접근 시 추가 DB 쿼리가 없어야 한다."""
        users = list(Post.objects.filter(email__iexact=self.EMAIL)[:2])
        with self.assertNumQueries(0):
            _ = users[0].price
            _ = users[1].name

    def test_ordering_newest_first(self):
        """ordering='-created' 이므로 두 번째 생성 Post가 users[0] 이어야 한다."""
        users = list(Post.objects.filter(email__iexact=self.EMAIL)[:2])
        self.assertEqual(users[0].name, "Second Booking")
        self.assertEqual(users[1].name, "First Booking")

    def test_safe_guard_when_only_one_post_exists(self):
        """Post가 1개뿐일 때 users[1]을 None으로 안전하게 처리해야 한다."""
        email = "single@example.com"
        _make_post(email, name="Only One")
        users = list(Post.objects.filter(email__iexact=email)[:2])
        user  = users[0] if len(users) > 0 else None
        user1 = users[1] if len(users) > 1 else None
        self.assertIsNotNone(user)
        self.assertIsNone(user1)

    def test_safe_guard_when_no_posts_exist(self):
        """Post가 없을 때 users[0], users[1] 모두 None이어야 한다."""
        users = list(Post.objects.filter(email__iexact="nobody@example.com")[:2])
        user  = users[0] if len(users) > 0 else None
        user1 = users[1] if len(users) > 1 else None
        self.assertIsNone(user)
        self.assertIsNone(user1)


# ===========================================================================
# 3. select_related('driver')
# ===========================================================================

@override_settings(CACHES=LOCMEM_CACHE)
class SelectRelatedDriverTest(TestCase):
    """select_related('driver') 를 사용하면 FK 접근 시 추가 쿼리가 없어야 한다."""

    EMAIL = "sr@example.com"

    def setUp(self):
        self.driver = _make_driver("Sam", driver_plate="XYZ999", driver_car="Honda")
        self.post   = _make_post(self.EMAIL, name="SR Test")
        self.post.driver = self.driver
        self.post.save(update_fields=["driver"])

    # ------------------------------------------------------------------
    def test_without_select_related_driver_access_triggers_extra_query(self):
        """select_related 없이 driver 필드 접근 시 추가 쿼리가 1번 발생한다 (비교 기준)."""
        post = Post.objects.filter(email=self.EMAIL).first()  # 1 query (outside block)
        with self.assertNumQueries(1):   # driver lazy-load
            _ = post.driver.driver_name

    def test_select_related_driver_access_no_extra_query(self):
        """select_related('driver') 로 조회 후 FK 필드 접근 시 추가 쿼리가 없어야 한다."""
        post = Post.objects.select_related("driver").filter(email=self.EMAIL).first()
        with self.assertNumQueries(0):
            name    = post.driver.driver_name
            contact = post.driver.driver_contact
            plate   = post.driver.driver_plate
            car     = post.driver.driver_car
        self.assertEqual(name, "Sam")
        self.assertEqual(plate, "XYZ999")

    def test_select_related_total_query_count_is_one(self):
        """조회부터 driver 필드 접근까지 전체 쿼리가 1번이어야 한다."""
        with self.assertNumQueries(1):
            post = Post.objects.select_related("driver").filter(email=self.EMAIL).first()
            _ = post.driver.driver_name
            _ = post.driver.driver_car

    def test_select_related_returns_correct_driver_data(self):
        """JOIN으로 로드된 driver 데이터가 DB와 일치해야 한다."""
        post = Post.objects.select_related("driver").filter(email=self.EMAIL).first()
        self.assertEqual(post.driver.driver_name, self.driver.driver_name)
        self.assertEqual(post.driver.driver_plate, self.driver.driver_plate)


# ===========================================================================
# 4. Q() 통합 (email | email1)
# ===========================================================================

@override_settings(CACHES=LOCMEM_CACHE)
class QObjectUnificationTest(TestCase):
    """Q(email | email1) 단일 쿼리로 기존 2번 조회를 대체해야 한다."""

    def setUp(self):
        self.post_by_email  = _make_post("primary@example.com", name="Primary Email User")
        self.post_by_email1 = _make_post(
            "other@example.com",
            name="Email1 User",
            email1="alt@example.com",
        )

    # ------------------------------------------------------------------
    def test_q_issues_single_db_query(self):
        """Q(email | email1) 조회는 DB를 1번만 조회해야 한다."""
        with self.assertNumQueries(1):
            result = Post.objects.filter(
                Q(email__iexact="primary@example.com")
                | Q(email1__iexact="primary@example.com")
            ).first()
        self.assertEqual(result.name, "Primary Email User")

    def test_q_finds_by_primary_email(self):
        """email 필드로 검색 시 올바른 Post를 반환해야 한다."""
        result = Post.objects.filter(
            Q(email__iexact="primary@example.com")
            | Q(email1__iexact="primary@example.com")
        ).first()
        self.assertEqual(result.name, "Primary Email User")

    def test_q_finds_by_email1_field(self):
        """email1 필드로만 매칭될 때도 올바른 Post를 반환해야 한다."""
        result = Post.objects.filter(
            Q(email__iexact="alt@example.com")
            | Q(email1__iexact="alt@example.com")
        ).first()
        self.assertEqual(result.name, "Email1 User")

    def test_q_vs_two_separate_queries_saves_one_query(self):
        """기존 or-chain(2 queries) 대비 Q() 통합(1 query)의 효과를 비교한다.

        email1-only 주소를 사용해 첫 번째 filter 가 None 을 반환하도록 강제해야
        or-chain 이 실제로 2번 DB를 조회한다.
        """
        email = "alt@example.com"  # post_by_email1 의 email1 값 — email 필드에는 없음

        # 기존 방식: 첫 filter 가 None → 두 번째 filter 실행 → 쿼리 2번
        with self.assertNumQueries(2):
            _ = (
                Post.objects.filter(email__iexact=email).first()
                or Post.objects.filter(email1__iexact=email).first()
            )

        # 개선 방식: Q() 통합 → 쿼리 1번
        with self.assertNumQueries(1):
            _ = Post.objects.filter(
                Q(email__iexact=email) | Q(email1__iexact=email)
            ).first()

    def test_q_returns_none_for_nonexistent_email(self):
        """매칭되는 레코드가 없을 때 None을 반환해야 한다."""
        result = Post.objects.filter(
            Q(email__iexact="nobody@example.com")
            | Q(email1__iexact="nobody@example.com")
        ).first()
        self.assertIsNone(result)


# ===========================================================================
# 5. bulk_update
# ===========================================================================

@override_settings(CACHES=LOCMEM_CACHE)
class BulkUpdateTest(TestCase):
    """bulk_update 는 행 수와 무관하게 쿼리 1번으로 업데이트해야 한다."""

    EMAIL = "bulk@example.com"
    N     = 5

    def setUp(self):
        self.posts = [
            _make_post(self.EMAIL, name=f"Booking {i}", price="100", paid="0")
            for i in range(self.N)
        ]

    # ------------------------------------------------------------------
    def test_bulk_update_issues_single_query(self):
        """N개 Post 업데이트 시 bulk_update 는 쿼리 1번이어야 한다."""
        posts = list(Post.objects.filter(email=self.EMAIL))
        for post in posts:
            post.paid     = "50"
            post.reminder = True
        with self.assertNumQueries(1):
            Post.objects.bulk_update(posts, ["paid", "reminder"], batch_size=50)

    def test_bulk_update_persists_all_values(self):
        """bulk_update 후 모든 행이 DB에 올바르게 저장되어야 한다."""
        posts = list(Post.objects.filter(email=self.EMAIL))
        for post in posts:
            post.paid     = "75"
            post.reminder = True
            post.cash     = False
        Post.objects.bulk_update(posts, ["paid", "reminder", "cash"], batch_size=50)

        refreshed = Post.objects.filter(email=self.EMAIL)
        for p in refreshed:
            self.assertEqual(p.paid, "75")
            self.assertTrue(p.reminder)
            self.assertFalse(p.cash)

    def test_individual_save_scales_linearly(self):
        """개별 save() 는 N개 행에 대해 N번 쿼리를 실행한다 (비교 기준)."""
        posts = list(Post.objects.filter(email=self.EMAIL))
        n = len(posts)
        for post in posts:
            post.paid = "10"
        with self.assertNumQueries(n):
            for post in posts:
                post.save(update_fields=["paid"])

    def test_bulk_update_query_count_independent_of_row_count(self):
        """bulk_update 쿼리 수는 행 수(5)와 무관하게 항상 1번이어야 한다."""
        posts = list(Post.objects.filter(email=self.EMAIL))
        self.assertEqual(len(posts), self.N)
        for post in posts:
            post.paid = "20"
        with self.assertNumQueries(1):
            Post.objects.bulk_update(posts, ["paid"], batch_size=50)

    def test_bulk_update_multiple_fields_still_one_query(self):
        """여러 필드를 동시에 업데이트해도 쿼리는 1번이어야 한다."""
        posts = list(Post.objects.filter(email=self.EMAIL))
        for post in posts:
            post.paid     = "30"
            post.notice   = "Gratitude applied"
            post.reminder = True
            post.toll     = ""
            post.cash     = False
            post.pending  = False
        with self.assertNumQueries(1):
            Post.objects.bulk_update(
                posts,
                ["paid", "notice", "reminder", "toll", "cash", "pending"],
                batch_size=50,
            )


# ===========================================================================
# 8. is_duplicate_submission() 캐시
# ===========================================================================

@override_settings(CACHES=LOCMEM_CACHE)
class IsDuplicateSubmissionTest(TestCase):
    """is_duplicate_submission() 는 DB 쿼리 없이 캐시 플래그로 중복을 감지해야 한다."""

    EMAIL = "dup@example.com"

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    # ------------------------------------------------------------------
    def test_first_call_returns_false(self):
        """첫 번째 제출은 중복이 아니므로 False를 반환해야 한다."""
        result = is_duplicate_submission(Post, self.EMAIL)
        self.assertFalse(result)

    def test_second_call_within_window_returns_true(self):
        """TTL 이내 두 번째 호출은 중복으로 감지되어 True를 반환해야 한다."""
        is_duplicate_submission(Post, self.EMAIL)   # 캐시 세팅
        result = is_duplicate_submission(Post, self.EMAIL)
        self.assertTrue(result)

    def test_after_cache_expiry_returns_false_again(self):
        """캐시 만료(삭제 시뮬레이션) 후 호출은 다시 False를 반환해야 한다."""
        is_duplicate_submission(Post, self.EMAIL)
        cache_key = f"submit_{Post.__name__}_{self.EMAIL}"
        cache.delete(cache_key)  # TTL 만료 시뮬레이션
        result = is_duplicate_submission(Post, self.EMAIL)
        self.assertFalse(result)

    def test_no_db_query_on_any_call(self):
        """첫 번째와 두 번째 호출 모두 DB 쿼리가 없어야 한다."""
        with self.assertNumQueries(0):
            is_duplicate_submission(Post, self.EMAIL)
        with self.assertNumQueries(0):
            is_duplicate_submission(Post, self.EMAIL)

    def test_different_emails_are_isolated(self):
        """서로 다른 이메일은 독립적인 캐시 키로 관리되어야 한다."""
        is_duplicate_submission(Post, "a@example.com")
        # b 는 아직 캐시 없음 → False
        self.assertFalse(is_duplicate_submission(Post, "b@example.com"))
        # a 는 캐시 있음 → True
        self.assertTrue(is_duplicate_submission(Post, "a@example.com"))

    def test_different_model_classes_are_isolated(self):
        """다른 모델 클래스는 독립적인 캐시 키를 가져야 한다."""
        is_duplicate_submission(Post, self.EMAIL)
        result = is_duplicate_submission(Inquiry, self.EMAIL)
        self.assertFalse(result)  # Inquiry 키는 별도 → 중복 아님

    def test_cache_key_format(self):
        """캐시 키가 submit_{ModelName}_{email} 형식이어야 한다."""
        is_duplicate_submission(Post, self.EMAIL)
        expected_key = f"submit_Post_{self.EMAIL}"
        self.assertIsNotNone(cache.get(expected_key))

    def test_real_ttl_expiry(self):
        """실제 1초 TTL이 만료된 후 False를 반환해야 한다 (실시간 TTL 검증)."""
        is_duplicate_submission(Post, self.EMAIL, seconds=1)
        self.assertTrue(is_duplicate_submission(Post, self.EMAIL, seconds=1))
        time.sleep(1.2)
        result = is_duplicate_submission(Post, self.EMAIL, seconds=1)
        self.assertFalse(result)
