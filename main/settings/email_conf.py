from decouple import config


EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT')
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_BACKEND = config('EMAIL_BACKEND')
# Django 기본값은 None(무한 대기)이다. 리마인더 크론은 메일을 한 통씩 동기로 보내므로
# Gmail이 응답을 멈추면 그 줄에서 영영 서고, 남은 예약은 알림 한 번 없이 발송되지 않는다.
EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=30, cast=int)

GMAIL_SERVICE_ACCOUNT_FILE = config('GMAIL_SERVICE_ACCOUNT_FILE')
CALENDAR_SERVICE_ACCOUNT_FILE = config('CALENDAR_SERVICE_ACCOUNT_FILE')

RECIPIENT_EMAIL = config('RECIPIENT_EMAIL')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL')
