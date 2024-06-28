from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.contrib.auth.decorators import user_passes_test
from basecamp.views import stripe_webhook


admin_site = user_passes_test(lambda u: u.is_superuser)(admin.site.urls)

urlpatterns = [  
    path('admin/', include('admin_honeypot.urls', namespace='admin_honeypot')),    
    path('horeb_yhwh/', admin.site.urls),
    path('markdownx/', include('markdownx.urls')),
    path('blog/', include('blog.urls')),
    path('easygo_review/', include('easygo_review.urls')),
    path('', include('basecamp.urls')),
    path('accounts/', include('allauth.urls')),
    path('static/<path:path>', serve, {'document_root': settings.STATIC_ROOT}),
    path('paypal/', include('paypal.standard.ipn.urls')),
    path('stripe_webhook/', stripe_webhook, name='stripe_webhook'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "EasyGo Administration"
admin.site.site_title = "EasyGo Administration"
admin.site.index_title = "EasyGo admin"
admin.site.block_title = "EasyGo Admin"
