from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.contrib.auth.decorators import user_passes_test
from basecamp.views import stripe_webhook
from blog.views import test_server_error, test_forbidden_view


admin_site = user_passes_test(lambda u: u.is_superuser)(admin.site.urls)

urlpatterns = [  
    path('admin/', include('admin_honeypot.urls', namespace='admin_honeypot')),    
    path('horeb_yhwh/', admin.site.urls),
    path('markdownx/', include('markdownx.urls')),
    path('blog/', include('blog.urls')),
    path('easygo_review/', include('easygo_review.urls')),
    path('', include('basecamp.urls')),
    path('accounts/', include('allauth.urls')),
    path('paypal/', include('paypal.standard.ipn.urls')),
    path('stripe_webhook/', stripe_webhook, name='stripe_webhook'),
    path('test-500/', test_server_error, name='test_server_error'),
    path('test-forbidden/', test_forbidden_view, name='test_forbidden'),
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
