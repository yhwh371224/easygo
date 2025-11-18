import sys
import os
import time

# Django 프로젝트 루트 경로 추가
sys.path.append('/home/horeb/github/easygo')

# Django 환경 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')
import django
django.setup()

from monitor.config import CHECK_INTERVAL
from monitor.fred_monitor import check_and_alert

def start_monitor():
    print("Starting FRED monitor scheduler...")
    while True:
        try:
            check_and_alert()
        except Exception as e:
            print("Monitor error:", e)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    start_monitor()


