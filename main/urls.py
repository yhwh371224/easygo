from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from email_agent.views import GmailWebhookView
from basecamp.views import stripe_webhook
from blog import bird_webhooks
from decouple import config

SECRET_ADMIN_URL = config('SECRET_ADMIN_URL', default='secure-admin-x9k2p7')

urlpatterns = [  
    path('admin/', include('admin_honeypot.urls', namespace='admin_honeypot')),
    path(f'{SECRET_ADMIN_URL}/', admin.site.urls),

    # Webhooks
    path('stripe_webhook/', stripe_webhook, name='stripe_webhook'),
    path('gmail_webhook/', GmailWebhookView.as_view(), name='gmail_webhook'),
    path('webhook/bird/sms/', bird_webhooks.sms_webhook, name='bird_sms_webhook'),
    path('webhook/bird/voice/', bird_webhooks.voice_webhook, name='bird_voice_webhook'),

    # Specific prefix apps
    path('markdownx/', include('markdownx.urls')),
    path('posting_agent/', include('posting_agent.urls', namespace='posting_agent')),  
    path('easygo_review/', include('easygo_review.urls')),
    path('articles/', include(('articles.urls', 'articles'), namespace='articles')),
    path('blog/', include(('blog.urls', 'blog'), namespace='blog')),
    path('accounts/', include('allauth.urls')),
    path('paypal/', include('paypal.standard.ipn.urls')),

    # Empty prefix apps - 맨 아래
    path('', include(('basecamp.urls', 'basecamp'), namespace='basecamp')),
    path('', include(('regions.urls', 'regions'), namespace='regions')),
    path('', include(('blog.urls', 'blog'), namespace='blog')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "EasyGo Administration"
admin.site.site_title = "EasyGo Administration"
admin.site.index_title = "EasyGo admin"
admin.site.block_title = "EasyGo Admin"

handler400 = 'blog.views.custom_bad_request'
handler403 = 'blog.views.custom_forbidden'
handler404 = 'blog.views.custom_page_not_found'
handler500 = 'blog.views.custom_server_error'
handler502 = 'blog.views.custom_bad_gateway'
handler503 = 'blog.views.custom_under_maintenance'
