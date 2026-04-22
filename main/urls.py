from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import user_passes_test
from basecamp.views import stripe_webhook
from email_agent.views import gmail_webhook
from blog import bird_webhooks


admin_site = user_passes_test(lambda u: u.is_superuser)(admin.site.urls)

urlpatterns = [  
    path('admin/', include('admin_honeypot.urls', namespace='admin_honeypot')),
    path('horeb_yhwh/', admin.site.urls),
    path('markdownx/', include('markdownx.urls')),
    path('posting_agent/', include('posting_agent.urls', namespace='posting_agent')),  
    path('easygo_review/', include('easygo_review.urls')),
    path('', include('articles.urls', namespace='articles')),
    path('', include('basecamp.urls')),
    path('accounts/', include('allauth.urls')),
    path('paypal/', include('paypal.standard.ipn.urls')),
    path('stripe_webhook/', stripe_webhook, name='stripe_webhook'),
    path('gmail_webhook/', gmail_webhook, name='gmail_webhook'),
    path('', include('blog.urls', namespace='blog')),
    path('webhook/bird/sms/', bird_webhooks.sms_webhook, name='bird_sms_webhook'),
    path('webhook/bird/voice/', bird_webhooks.voice_webhook, name='bird_voice_webhook'),
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
