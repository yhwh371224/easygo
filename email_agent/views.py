import json
import base64
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from .tasks import gmail_watch_topic


@csrf_exempt
def gmail_webhook(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        # Pub/Sub 메시지 디코딩
        pubsub_message = data.get('message', {})
        if pubsub_message:
            message_data = base64.b64decode(
                pubsub_message['data']
            ).decode('utf-8')
            payload = json.loads(message_data)
            
            # 여기서 Celery task로 넘김
            gmail_watch_topic.delay(payload)
        
        return HttpResponse(status=200)