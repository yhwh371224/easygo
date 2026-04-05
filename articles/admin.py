from django.contrib import admin
from .models import Category, Tag, Post


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ('name', 'slug', 'order')
    prepopulated_fields = {'slug': ('name',)}
    ordering      = ('order', 'name')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display  = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display  = ('title', 'category', 'status', 'is_featured',
                     'view_count', 'published_at')
    list_filter   = ('status', 'is_featured', 'category', 'tags')
    search_fields = ('title', 'excerpt', 'content')
    prepopulated_fields  = {'slug': ('title',)}
    readonly_fields      = ('view_count', 'created_at', 'updated_at', 'published_at')
    filter_horizontal    = ('tags',)

    # SNS 발행 상태는 나중에 posting_agent 연동 후 활성화
    # list_display 에 posted_to_google, posted_to_facebook, posted_to_instagram 추가 예정

    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'excerpt', 'content', 'thumbnail', 'thumbnail_query', 'thumbnail_source_url')
        }),
        ('Classification', {
            'fields': ('category', 'tags')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',),
        }),
        ('Publishing', {
            'fields': ('status', 'is_featured')
        }),
        ('SNS (posting_agent)', {
            'fields': ('posted_to_google', 'posted_to_facebook', 'posted_to_instagram', 'gmb_content'),
            'classes': ('collapse',),
        }),
        ('Stats', {
            'fields': ('view_count', 'created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',),
        }),
    )