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



