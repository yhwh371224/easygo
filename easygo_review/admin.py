from django.contrib import admin
from django.contrib.admin import AdminSite
from .models import Post, Comment


class PostAdmin(admin.ModelAdmin):
    list_display = ['date', 'name', 'is_published', 'created']
    search_fields = ['date', 'name']


class CommentAdmin(admin.ModelAdmin):
    list_display = ['post', 'author', 'created_at', 'modified_at']
    search_fields = ['author', 'created_at', 'modified_at']


class MyAdminSite(AdminSite):
    site_header = 'EasyGo administration'

admin_site = MyAdminSite(name='horeb_yhwh')
admin_site.register(Post, PostAdmin)
admin_site.register(Comment, CommentAdmin)


admin.site.register(Comment, CommentAdmin)
admin.site.register(Post, PostAdmin)
