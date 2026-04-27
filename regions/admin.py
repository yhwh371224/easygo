from django.contrib import admin

from .models import Region, RegionSuburb


class RegionSuburbInline(admin.TabularInline):
    model = RegionSuburb
    extra = 1
    fields = ('name', 'slug', 'zone', 'price', 'is_active', 'is_pinned', 'sort_order', 'meta_title')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'airport_code', 'state_code', 'phone', 'phone_display', 'is_active')
    list_editable = ('is_active',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [RegionSuburbInline]
    fieldsets = (
        (None, {
            'fields': ('slug', 'name', 'state_code', 'timezone', 'is_active'),
        }),
        ('Airport', {
            'fields': ('airport_code', 'airport_name', 'airport_lat', 'airport_lng'),
        }),
        ('Contact & Location', {
            'fields': ('phone', 'phone_display', 'address', 'latitude', 'longitude'),
        }),
        ('SEO', {
            'fields': ('meta_description',),
        }),
        ('Guides & Terminals', {
            'fields': ('terminal_info', 'meeting_point', 'arrival_guide'),
            'classes': ('collapse',),
        }),
    )


@admin.register(RegionSuburb)
class RegionSuburbAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'zone', 'price', 'is_active', 'is_pinned')
    list_filter = ('region', 'zone', 'is_active', 'is_pinned')
    list_editable = ('price', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'slug')
    fieldsets = (
        (None, {
            'fields': ('region', 'name', 'slug', 'zone', 'price', 'is_active'),
        }),
        ('Dropdown ordering', {
            'fields': ('is_pinned', 'sort_order'),
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',),
        }),
    )
