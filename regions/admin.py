from django.contrib import admin
from .models import Region


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'airport_code', 'timezone', 'phone', 'is_active')
    list_editable = ('is_active',)
    prepopulated_fields = {'slug': ('name',)}
