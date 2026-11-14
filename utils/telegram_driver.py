"""드라이버 전용 텔레그램 봇 클라이언트.

관리자 알림 봇(utils/telegram.py)과 토큰이 다르다. 이 봇은 드라이버 개인 채팅으로
픽업 2시간 전 알림과 확인 버튼을 보내고, webhook(blog/telegram_driver_webhook.py)으로
/start 연결과 버튼 클릭을 받는다.

텔레그램 봇은 상대가 먼저 /start 를 보내야만 메시지를 보낼 수 있다. 그래서 드라이버는
대시보드의 deep link(t.me/<bot>?start=<token>)로 한 번 연결해 chat id 를 남긴다.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TIMEOUT = 10
# 이 상태코드는 재시도해도 안 된다 — 드라이버가 봇을 차단(403)했거나 chat id 가
# 잘못됐다(400). 호출부는 이걸 보고 매 실행마다 같은 실패를 반복하지 않는다.
PERMANENT_ERROR_CODES = (400, 403)


class TelegramDriverError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code

    @property
    def permanent(self):
        return self.status_code in PERMANENT_ERROR_CODES


def is_configured():
    return bool(settings.TELEGRAM_DRIVER_BOT_TOKEN)


def link_url(token):
    """드라이버 대시보드의 연결 버튼 주소. 봇 이름이 없으면 None."""
    username = (settings.TELEGRAM_DRIVER_BOT_USERNAME or '').lstrip('@')
    if not (username and token and is_configured()):
        return None
    return f'https://t.me/{username}?start={token}'


def call(method, **payload):
    """Bot API 호출. 실패하면 TelegramDriverError 를 던진다(조용히 삼키지 않는다 —
    발송 실패를 관리자에게 알려야 드라이버에게 전화라도 할 수 있다)."""
    token = settings.TELEGRAM_DRIVER_BOT_TOKEN
    if not token:
        raise TelegramDriverError('TELEGRAM_DRIVER_BOT_TOKEN is not set')
    url = f'https://api.telegram.org/bot{token}/{method}'
    try:
        resp = requests.post(url, json=payload, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise TelegramDriverError(f'{method} request failed: {exc}') from exc
    try:
        data = resp.json()
    except ValueError:
        data = {}
    if not resp.ok or not data.get('ok'):
        description = data.get('description') or resp.text[:300]
        raise TelegramDriverError(f'{method} failed ({resp.status_code}): {description}',
                                  status_code=resp.status_code)
    return data.get('result')


def send_message(chat_id, text, buttons=None):
    """plain text 로 보낸다 — 주소/편명에 _ * [ 가 섞이면 Markdown 이 400 으로 떨어진다.
    buttons 는 inline keyboard 행 목록([[{text, url|callback_data}, ...], ...])."""
    payload = {'chat_id': chat_id, 'text': text, 'disable_web_page_preview': True}
    if buttons:
        payload['reply_markup'] = {'inline_keyboard': buttons}
    return call('sendMessage', **payload)


def answer_callback(callback_query_id, text=''):
    return call('answerCallbackQuery', callback_query_id=callback_query_id, text=text)


def edit_message(chat_id, message_id, text, buttons=None):
    payload = {'chat_id': chat_id, 'message_id': message_id, 'text': text,
               'disable_web_page_preview': True}
    payload['reply_markup'] = {'inline_keyboard': buttons or []}
    return call('editMessageText', **payload)
