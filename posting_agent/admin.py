from django.contrib import admin
from posting_agent.models import BlogPost


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'blog_status', 'published_at', 'created_at']
    list_filter = ['blog_status']
    search_fields = ['title']
    prepopulated_fields = {'slug': ('title',)}
