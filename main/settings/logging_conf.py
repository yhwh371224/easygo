import logging
import os

from decouple import config

from .base import BASE_DIR


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },

    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/django.log'),
            'formatter': 'verbose',
        },
        'email_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/email_reminders.log'),
            'formatter': 'verbose',
        },
        'sms_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/sms.log'),
            'formatter': 'verbose',
        },
        'email_agent_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/email_agent.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'telegram': {
            'level': 'ERROR',
            'class': 'telegram_handler.TelegramHandler',
            'token': config('TELEGRAM_BOT_TOKEN'),
            'chat_id': config('TELEGRAM_CHAT_ID'),
        },
        'inquiry_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/inquiry.log'),
            'formatter': 'verbose',
        },
    },

    'loggers': {
        'django': {
            'handlers': ['file', 'telegram'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # 템플릿의 {{ var|default:... }} 가 없는 변수를 찾을 때마다 남기는
        # VariableDoesNotExist DEBUG 로그(정상 동작)가 django.log 를 뒤덮지 않게 한다.
        'django.template': {
            'handlers': ['file', 'telegram'],
            'level': 'INFO',
            'propagate': False,
        },
        'blog.management.commands.booking_reminder': {
            'handlers': ['email_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'bird_webhooks': {
            'handlers': ['sms_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'bird_proxy': {
            'handlers': ['sms_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'sms': {
            'handlers': ['sms_file', 'telegram'],
            'level': 'INFO',
            'propagate': False,
        },
        'easygo': {
            'handlers': ['file', 'console', 'telegram'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'email_agent': {
            'handlers': ['email_agent_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'blog': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'basecamp': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'regions': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        # utils.telegram 이 알림 전송 실패를 여기로 남긴다. 루트로 흘리면
        # lastResort 핸들러가 stderr 로만 뱉어서 크론 로그마다 흩어진다.
        'utils': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'inquiry': {
            'handlers': ['inquiry_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },        
    },
}

logging.getLogger('django.security.DisallowedHost').setLevel(logging.CRITICAL)
