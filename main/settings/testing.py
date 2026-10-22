import sys


# `manage.py test` 에서만 적용 — 테스트가 운영 Redis(Celery 큐·캐시)에 닿지 않게 한다.
# 실서버에서 테스트를 돌려도 .delay() 가 운영 워커로 가서 운영 DB 를 조회하거나,
# cache.clear() 가 운영 캐시를 비우는 일이 없도록. 그 외 운영 설정은 건드리지 않는다.
TESTING = len(sys.argv) > 1 and sys.argv[1] == 'test'

if TESTING:
    CELERY_BROKER_URL = 'memory://'
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'easygo-tests',
        }
    }
