from decouple import config

from .base import ENVIRONMENT


CELERY_BROKER_URL = config('CELERY_BROKER', 'redis://127.0.0.1:6379')
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Australia/Sydney'
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

if ENVIRONMENT != 'production':
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
