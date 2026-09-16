import logging

from django.core.validators import validate_email
from django.shortcuts import render
from django.utils import timezone
from django_ratelimit.decorators import ratelimit

from basecamp.modules.view_helpers import verify_turnstile, get_client_ip
from main.settings import RECIPIENT_EMAIL
from utils.email import send_template_email, send_text_email
from utils.telegram import send_telegram_sync

logger = logging.getLogger(__name__)

PAGE_CHOICES = ['Page 1', 'Page 2', 'Page 3', 'Page 4+', "Couldn't find it"]
LANDED_CHOICES = [
    'Yes, the homepage loaded straight away',
    'No, a different page loaded',
    "Couldn't find EasyGo to click on",
]

FIELD_MAX_LENGTHS = {
    'name': 100, 'email': 254, 'keyword': 200,
    'landed_note': 300, 'liked': 4000, 'improve': 4000,
}


def _is_valid_email(value):
    try:
        validate_email(value)
        return True
    except Exception:
        return False


def _notify_search_survey(response):
    message = """New Search Survey Response
=====================
Name: {name}
Email: {email}

1) Search term: {keyword}
2) Page EasyGo appeared on: {page}
3) Did the homepage load straight away?: {landed}{landed_note}
4) What they liked: {liked}
5) What could be improved: {improve}
{code_line}""".format(
        name=response.name,
        email=response.email,
        keyword=response.keyword,
        page=response.page,
        landed=response.landed,
        landed_note=(' - ' + response.landed_note) if response.landed_note else '',
        liked=response.liked or '(not answered)',
        improve=response.improve or '(not answered)',
        code_line=(f"\nDiscount code issued: {response.discount_code} "
                   f"(${response.discount_amount})\n") if response.discount_code else '',
    )

    subject = f"[Search Survey] {response.name} - {response.page}"
    try:
        send_text_email(subject, message, [RECIPIENT_EMAIL])
    except Exception:
        logger.exception("search_survey: failed to send email for %s", response.email)

    telegram_text = (
        f"🔍 *New Search Survey Response*\n"
        f"Name: {response.name}\n"
        f"Keyword: {response.keyword}\n"
        f"Page: {response.page}\n"
        f"Landed: {response.landed}"
    )
    try:
        send_telegram_sync(telegram_text)
    except Exception:
        logger.exception("search_survey: failed to send telegram for %s", response.email)


def _send_discount_code(response):
    """설문 페이지에서 약속한 할인 코드를 참여자 본인에게 보낸다.
    보낸 시각을 남겨서 admin 에서 '메일 나갔나' 를 눈으로 확인할 수 있게 한다."""
    context = {
        'name': response.name,
        'email': response.email,
        'discount_code': response.discount_code,
        'discount_amount': response.discount_amount,
        'discount_expires': response.discount_expires,
    }
    send_template_email(
        f"Your EasyGo discount code — {response.discount_code}",
        'html_email-search-survey-discount.html',
        context,
        [response.email],
    )
    response.discount_emailed = timezone.now()
    response.save(update_fields=['discount_emailed'])


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def search_survey(request):
    """Public feedback form: testers search Google for EasyGo, click through,
    and report what they found. Saved to SearchSurveyResponse (queryable in
    admin) and mirrored out via email + Telegram so it's seen right away —
    same pattern as blog.driver_views.driver_apply."""
    from easygo_review.models import SearchSurveyResponse

    error = None
    submitted = False
    discount_code = discount_amount = discount_expires = None
    form_data = {
        'name': '', 'email': '', 'keyword': '', 'page': '',
        'landed': '', 'landed_note': '', 'liked': '', 'improve': '',
    }

    if request.method == 'POST':
        for field in form_data:
            form_data[field] = (request.POST.get(field) or '').strip()

        token = request.POST.get('cf-turnstile-response', '')
        required = ['name', 'email', 'keyword', 'page', 'landed']

        if not verify_turnstile(token, get_client_ip(request)):
            error = 'Security verification failed. Please try again.'
        elif not all(form_data[f] for f in required):
            error = 'Please fill in the required fields.'
        elif any(len(form_data[f]) > limit for f, limit in FIELD_MAX_LENGTHS.items()):
            error = 'One of the fields is too long — please shorten it.'
        elif form_data['page'] not in PAGE_CHOICES:
            error = 'Please choose a valid page option.'
        elif form_data['landed'] not in LANDED_CHOICES:
            error = 'Please choose a valid answer for step 3.'
        elif not _is_valid_email(form_data['email']):
            error = 'Please enter a valid email address.'

        if not error:
            response = SearchSurveyResponse.objects.create(**form_data)

            # 할인 코드 자동 발급/발송 보류 (2026-09-16). 설문에 참여했다고
            # 할인까지 주는 건 과하다고 판단해서 페이지의 약속 문구와 함께 껐다.
            # 모델 필드 / 코드 생성 / 메일 템플릿 / admin 액션은 그대로 살아있으니,
            # 다시 주기로 하면 아래 네 줄과 search_survey.html 의 안내 블록만
            # 되살리면 된다. (admin 의 'Re-send discount code email' 액션으로
            # 지금도 건건이 수동 발급은 가능하다.)
            #
            # response.issue_discount_code()
            # try:
            #     _send_discount_code(response)
            # except Exception:
            #     logger.exception("search_survey: failed to email discount code to %s",
            #                      response.email)
            # discount_code = response.discount_code
            # discount_amount = response.discount_amount
            # discount_expires = response.discount_expires

            _notify_search_survey(response)
            submitted = True
            form_data = {k: '' for k in form_data}

    return render(request, 'basecamp/pages/search_survey.html', {
        'error': error,
        'submitted': submitted,
        'form_data': form_data,
        'page_choices': PAGE_CHOICES,
        'landed_choices': LANDED_CHOICES,
        'discount_code': discount_code,
        'discount_amount': discount_amount,
        'discount_expires': discount_expires,
    })
