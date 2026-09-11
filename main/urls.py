import os
import re

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from email_agent.views import GmailWebhookView
from basecamp.views import stripe_webhook
from blog import bird_webhooks, driver_views
from decouple import config


def serve_sitemap(request, filename):
    path_ = os.path.join(settings.BASE_DIR, 'sitemaps', filename)
    if not os.path.exists(path_) or not re.fullmatch(r'sitemap[\w\-]*\.xml', filename):
        raise Http404
    return FileResponse(open(path_, 'rb'), content_type='application/xml')


# TWA (Trusted Web Activity) Digital Asset Links verification for the
# EasyGo Driver Android app on Play Store. Two fingerprints are listed
# because Play App Signing re-signs the distributed app with a Google-held
# key, so both the original PWABuilder upload keystore (used to sign the
# uploaded AAB) and the Play App Signing certificate (what actually ships
# to users) need to verify.
def serve_assetlinks(request):
    return JsonResponse([{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {
            "namespace": "android_app",
            "package_name": "au.com.easygoshuttle.driver",
            "sha256_cert_fingerprints": [
                "F3:11:B8:63:D5:C6:55:BB:6D:D2:D3:00:54:0E:9B:E3:2A:44:3B:D3:8D:7D:36:17:F2:4D:93:AA:A1:D7:A8:49",
                "EA:44:59:DE:05:63:EA:58:A3:EF:6A:B6:AA:B8:62:B8:7F:77:23:45:3E:01:CA:7D:62:A6:43:A5:FA:9A:A6:96",
            ],
        },
    }], safe=False)

# nginx serves .webmanifest as application/octet-stream and we send
# X-Content-Type-Options: nosniff, so Chrome refuses to parse the manifest off
# /static/ — which also makes PWABuilder report "no manifest". Serving it here
# pins the right type without needing an nginx change. The path stays under
# /driver/ because DriverAccessRestrictionMiddleware bounces logged-in drivers
# off every other prefix, and they are the ones whose Chrome fetches this.
DRIVER_MANIFEST = os.path.join(
    settings.BASE_DIR, 'basecamp', 'static', 'basecamp', 'favi',
    'driver-manifest.webmanifest')


def serve_driver_manifest(request):
    with open(DRIVER_MANIFEST, 'rb') as fh:
        return HttpResponse(fh.read(), content_type='application/manifest+json')


SECRET_ADMIN_URL = config('SECRET_ADMIN_URL', default='secure-admin-x9k2p7')

urlpatterns = [
    re_path(r'^(?P<filename>sitemap[\w\-]*\.xml)$', serve_sitemap, name='sitemap'),
    path('.well-known/assetlinks.json', serve_assetlinks, name='assetlinks'),
    path('driver/manifest.webmanifest', serve_driver_manifest,
         name='driver_manifest'),

    path('admin/', include('admin_honeypot.urls', namespace='admin_honeypot')),
    path(f'{SECRET_ADMIN_URL}/', admin.site.urls),

    # Webhooks
    path('stripe_webhook/', stripe_webhook, name='stripe_webhook'),
    path('gmail_webhook/', GmailWebhookView.as_view(), name='gmail_webhook'),
    # The channel in the path is how we know which of our numbers was dialled.
    # The bare paths are the legacy subscriptions; sync_bird_channels moves them.
    path('webhook/bird/sms/', bird_webhooks.sms_webhook, name='bird_sms_webhook'),
    path('webhook/bird/voice/', bird_webhooks.voice_webhook, name='bird_voice_webhook'),
    path('webhook/bird/sms/<uuid:channel_id>/', bird_webhooks.sms_webhook,
         name='bird_sms_webhook_channel'),
    path('webhook/bird/voice/<uuid:channel_id>/', bird_webhooks.voice_webhook,
         name='bird_voice_webhook_channel'),

    # Specific prefix apps
    path('markdownx/', include('markdownx.urls')),
    path('easygo_review/', include('easygo_review.urls')),
    path('articles/', include(('articles.urls', 'articles'), namespace='articles')),
    path('accounts/', include('allauth.urls')),
    path('paypal/', include('paypal.standard.ipn.urls')),
    path('partner/', include(('blog.apply_urls', 'blog_apply'), namespace='blog_apply')),
    # /driver/apply/ kept live alongside /partner/apply/ (both serve the same
    # form) since old links/ads/bookmarks may point here. Page is
    # noindex,nofollow so two live paths isn't an SEO duplicate-content issue.
    # The step-2 continuation only exists at /driver/apply/account/ (in blog/urls.py).
    path('driver/apply/', driver_views.driver_apply, name='driver_apply_legacy'),
    path('driver/', include(('blog.urls', 'blog'), namespace='blog')),

    # Empty prefix apps - 맨 아래
    path('', include(('basecamp.urls', 'basecamp'), namespace='basecamp')),
    path('', include(('regions.urls', 'regions'), namespace='regions')),
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
