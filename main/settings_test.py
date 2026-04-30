"""
Test-only settings: swaps PostgreSQL → SQLite and disables Redis/Celery
so the test suite runs without external services.
"""
from main.settings import *  # noqa: F401, F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable rate limiting in test environment (tests can exceed per-minute limits).
RATELIMIT_ENABLE = False

# Tests should not depend on collectstatic/manifest static files.
STORAGES = {
    **STORAGES,
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
