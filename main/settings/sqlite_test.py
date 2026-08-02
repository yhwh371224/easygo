"""로컬 테스트용 설정 — 인메모리 sqlite + 마이그레이션 비활성화.

개발 머신의 postgres 롤에 CREATEDB 권한이 없어 `manage.py test` 가 테스트 DB를
만들지 못한다. 마이그레이션을 끄면 모델에서 바로 스키마를 만들기 때문에
postgres 전용 마이그레이션 연산(AddIndexConcurrently 등)도 우회된다.

    python manage.py test blog --settings=main.settings.sqlite_test

실서버/운영에서는 쓰지 않는다.
"""
from main.settings import *  # noqa


class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
MIGRATION_MODULES = DisableMigrations()
