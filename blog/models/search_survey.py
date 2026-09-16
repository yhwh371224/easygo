import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


# 사람이 전화로 불러주고 받아적는 코드라서 헷갈리는 글자(0/O, 1/I/L)는 뺐다.
CODE_ALPHABET = '23456789ABCDEFGHJKMNPQRSTUVWXYZ'
CODE_LENGTH = 6
CODE_PREFIX = 'EG'


def generate_discount_code():
    """EG-XXXXXX 형태의 미사용 코드를 만든다. 중복이면 다시 뽑는다."""
    for _ in range(20):
        body = ''.join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        code = f'{CODE_PREFIX}-{body}'
        if not SearchSurveyResponse.objects.filter(discount_code=code).exists():
            return code
    raise RuntimeError('could not generate a unique survey discount code')


class SearchSurveyResponse(models.Model):
    """A tester's answers from the 'search for EasyGo on Google' feedback
    page (basecamp:search_survey) — used to check how findable the site is
    and collect first-impression feedback on the homepage.

    설문에 참여하면 할인 코드를 메일로 보내주기로 약속했으므로, 응답 한 건이
    곧 코드 한 장이다. 별도 쿠폰 모델을 두지 않고 여기에 코드/금액/만료/사용
    여부를 같이 들고 있는다 — 예약의 discount 는 어차피 사람이 손으로 넣는다."""

    name = models.CharField(max_length=100)
    email = models.EmailField()
    keyword = models.CharField(max_length=200)
    page = models.CharField(max_length=50)
    landed = models.CharField(max_length=100)
    landed_note = models.CharField(max_length=300, blank=True)
    liked = models.TextField(blank=True)
    improve = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    discount_code = models.CharField(max_length=20, blank=True, unique=True, null=True)
    discount_amount = models.PositiveIntegerField(default=0, help_text='달러 정액 할인')
    discount_expires = models.DateField(null=True, blank=True)
    discount_emailed = models.DateTimeField(null=True, blank=True)
    discount_redeemed = models.DateTimeField(null=True, blank=True)
    discount_redeemed_note = models.CharField(max_length=200, blank=True,
                                              help_text='어느 예약에 썼는지 메모')

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"{self.name} — {self.keyword} ({self.page})"

    def issue_discount_code(self):
        """코드가 없으면 설정값대로 발급한다. 이미 있으면 그대로 둔다."""
        if self.discount_code:
            return self.discount_code
        self.discount_code = generate_discount_code()
        self.discount_amount = settings.SURVEY_DISCOUNT_AMOUNT
        self.discount_expires = (
            timezone.localdate() + timedelta(days=settings.SURVEY_DISCOUNT_VALID_DAYS)
        )
        self.save(update_fields=['discount_code', 'discount_amount', 'discount_expires'])
        return self.discount_code

    @property
    def discount_is_valid(self):
        if not self.discount_code or self.discount_redeemed:
            return False
        return not self.discount_expires or self.discount_expires >= timezone.localdate()
