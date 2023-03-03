import os
from celery import Celery
from datetime import timedelta
from celery.schedules import crontab

 
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')
app = Celery('main')
app.config_from_object('django.conf:settings', namespace='CELERY')
 
app.conf.timezone = 'Australia/Sydney'
 
app.conf.beat_schedule = {
    "email_1": {
        "task": "blog.tasks.email_1", 
        "schedule": crontab(hour=0, minute=10)},
    "email_2": {
        "task": "blog.tasks.email_2", 
        "schedule": crontab(hour=0, minute=10)},
    "email_3": {
        "task": "blog.tasks.email_3", 
        "schedule": crontab(hour=0, minute=10)},
    "email_4": {
        "task": "blog.tasks.email_4", 
        "schedule": crontab(hour=0, minute=10)},
    "email_5": {
        "task": "blog.tasks.email_5", 
        "schedule": crontab(hour=0, minute=10)},
    "email_6": {
        "task": "blog.tasks.email_6", 
        "schedule": crontab(hour=0, minute=10)},   
    }

# app.conf.beat_schedule = {
#    "email_1": {
#        "task": "blog.tasks.email_1", 
#        "schedule": timedelta(seconds=30)},
#    "email_2": {
#        "task": "blog.tasks.email_2", 
#        "schedule": timedelta(seconds=30)},
#    "email_3": {
#        "task": "blog.tasks.email_3", 
#        "schedule": timedelta(seconds=30)},
#    "email_4": {
#        "task": "blog.tasks.email_4", 
#        "schedule": timedelta(seconds=30)},
#    "email_5": {
#        "task": "blog.tasks.email_5", 
#        "schedule": timedelta(seconds=30)},
#    "email_6": {
#        "task": "blog.tasks.email_6", 
#        "schedule": timedelta(seconds=30)},#   
#    }
 
app.autodiscover_tasks()
