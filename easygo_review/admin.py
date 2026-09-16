from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils import timezone

from .models import Post, Comment, SearchSurveyResponse


class PostAdmin(admin.ModelAdmin):
    list_display = ['date', 'name', 'is_published', 'created']
    search_fields = ['date', 'name']


class CommentAdmin(admin.ModelAdmin):
    list_display = ['post', 'author', 'created_at', 'modified_at']
    search_fields = ['author', 'created_at', 'modified_at']


class SearchSurveyResponseAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'keyword', 'page', 'landed',
                    'discount_code', 'discount_amount', 'code_status', 'created']
    search_fields = ['name', 'email', 'keyword', 'discount_code']
    list_filter = ['page', 'landed', 'discount_redeemed']
    readonly_fields = ['created', 'discount_code', 'discount_emailed']
    ordering = ['-created']
    actions = ['mark_code_redeemed', 'resend_discount_code']

    @admin.display(description='Code status')
    def code_status(self, obj):
        if not obj.discount_code:
            return '—'
        if obj.discount_redeemed:
            return f"used {obj.discount_redeemed:%d/%m/%y}"
        if not obj.discount_is_valid:
            return 'expired'
        return 'sent' if obj.discount_emailed else 'NOT EMAILED'

    @admin.action(description='Mark discount code as used')
    def mark_code_redeemed(self, request, queryset):
        updated = queryset.filter(discount_redeemed__isnull=True).update(
            discount_redeemed=timezone.now())
        self.message_user(request, f"{updated} code(s) marked as used.")

    @admin.action(description='Re-send discount code email')
    def resend_discount_code(self, request, queryset):
        from easygo_review.search_survey_views import _send_discount_code
        sent = failed = 0
        for response in queryset:
            response.issue_discount_code()
            try:
                _send_discount_code(response)
                sent += 1
            except Exception:
                failed += 1
        msg = f"{sent} code email(s) sent."
        if failed:
            msg += f" {failed} failed — check the logs."
        self.message_user(request, msg)


class MyAdminSite(AdminSite):
    site_header = 'EasyGo administration'

admin_site = MyAdminSite(name='horeb_yhwh')
admin_site.register(Post, PostAdmin)
admin_site.register(Comment, CommentAdmin)
admin_site.register(SearchSurveyResponse, SearchSurveyResponseAdmin)


admin.site.register(Comment, CommentAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(SearchSurveyResponse, SearchSurveyResponseAdmin)
