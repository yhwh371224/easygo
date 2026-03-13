# main/tasks.py
from celery import shared_task

@shared_task
def gmail_watch_topic(payload):
    # 여기서 실제 Gmail API 호출로 메시지 처리
    print("Processing payload:", payload)