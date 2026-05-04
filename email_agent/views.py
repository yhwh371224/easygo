# email_agent/views.py
import json
import base64
from django.http import HttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .tasks import gmail_watch_topic

@method_decorator(csrf_exempt, name='dispatch')
class GmailWebhookView(View):
    def post(self, request):
        data = json.loads(request.body)
        pubsub_message = data.get('message', {})
        if pubsub_message:
            message_data = base64.b64decode(
                pubsub_message['data']
            ).decode('utf-8')
            payload = json.loads(message_data)
            gmail_watch_topic.apply_async(args=[payload], countdown=10)
        return HttpResponse(status=200)