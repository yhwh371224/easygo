# Django shortcuts

mm:
	python3 manage.py makemigrations

mig:
	python3 manage.py migrate

mmig:
	python3 manage.py makemigrations && python manage.py migrate

dev:
	python3 manage.py runserver

shell:
	python3 manage.py shell

superuser:
	python3 manage.py createsuperuser

cst:
	python3 manage.py collectstatic --noinput

article:
	python3 manage.py generate_article

bot:
	python3 manage.py run_telegram_bo

check:
	python3 manage.py check

pytest:
	pytest -v --cov=. --cov-report=term-missing

testflow:
	pytest tests/test_terminal_flow.py -v

blockip:
	python3 manage.py reload_blocked

# 결제 독촉 — 발송/취소 없이 대상만 확인
dunning-dry:
	python3 manage.py no_payment_yet --dry-run
	python3 manage.py auto_cancel_pending --dry-run

