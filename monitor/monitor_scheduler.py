import sys
import os
import django
import time

# 1️⃣ 프로젝트 루트 경로 추가 (monitor 모듈 탐색용)
sys.path.insert(0, '/home/horeb/github/easygo')

# 2️⃣ Django 환경 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')
django.setup()

# 3️⃣ 모니터 모듈 import
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


