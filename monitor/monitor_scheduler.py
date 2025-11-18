import time
from monitor.config import CHECK_INTERVAL
from monitor.fred_monitor import check_and_alert

def start_monitor(request=None):
    print("Starting FRED monitor scheduler...")
    while True:
        try:
            check_and_alert(request)
        except Exception as e:
            print("Monitor error:", e)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    start_monitor()


