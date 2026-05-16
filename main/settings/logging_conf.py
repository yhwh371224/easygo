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
    },

    'loggers': {
        'django': {
            'handlers': ['file', 'telegram'],
            'level': 'DEBUG',
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
            'handlers': ['sms_file'],
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
    },
}

logging.getLogger('django.security.DisallowedHost').setLevel(logging.CRITICAL)
