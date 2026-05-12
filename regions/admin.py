from django.contrib import admin

from .models import (
    Country,
    Region,
    RegionSuburb,
    Airport,
    Terminal,
    TerminalPickupPoint,
    PickupPointMap,
)


class PickupPointMapInline(admin.TabularInline):
    model = PickupPointMap
    extra = 1


@admin.register(TerminalPickupPoint)
class TerminalPickupPointAdmin(admin.ModelAdmin):
    list_display = ("terminal", "name")
    list_filter = ("terminal__airport",)
    inlines = [PickupPointMapInline]


class TerminalPickupPointInline(admin.StackedInline):
    model = TerminalPickupPoint
    extra = 1
    show_change_link = True
    fields = ("name", "instruction")


@admin.register(Terminal)
class TerminalAdmin(admin.ModelAdmin):
    list_display = ("airport", "name", "type")
    inlines = [TerminalPickupPointInline]


class TerminalInline(admin.TabularInline):
    model = Terminal
    extra = 1
    fields = ("name", "type")


@admin.register(Airport)
class AirportAdmin(admin.ModelAdmin):
    list_display = ("code", "city", "name", "country")
    search_fields = ("code", "city", "name")
    ordering = ("code",)
    inlines = [TerminalInline]


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class RegionSuburbInline(admin.TabularInline):
    model = RegionSuburb
    extra = 1
    fields = ("name", "slug", "zone", "price", "is_active", "is_pinned", "sort_order", "meta_title")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "primary_airport", "state_code", "phone", "phone_display", "is_active", "is_coming_soon")
    list_editable = ("is_active", "is_coming_soon")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [RegionSuburbInline]
    fieldsets = (
        (None, {
            "fields": ("slug", "name", "state_code", "timezone", "is_active", "is_coming_soon"),
        }),
        ("Airports", {
            "fields": ("primary_airport", "airports"),
        }),
        ("Contact & Location", {
            "fields": ("phone", "phone_display", "address", "latitude", "longitude"),
        }),
        ("SEO", {
            "fields": ("meta_title", "meta_description"),
        }),
        ("Hero Image", {
            "fields": ("hero_image",),
            "description": "Filename only (e.g. melbourneairport.webp). Leave blank to use {slug}airport.webp automatically.",
        }),
        ("Guides & Terminals (legacy — remove after template migration)", {
            "fields": ("terminal_info", "meeting_point", "arrival_guide"),
            "classes": ("collapse",),
        }),
    )


@admin.register(RegionSuburb)
class RegionSuburbAdmin(admin.ModelAdmin):
    ordering = ("region", "-is_pinned", "-is_featured", "sort_order", "name")
    list_display = ("name", "region", "zone", "price", "is_active", "is_pinned", "is_featured")
    list_filter = ("region", "zone", "is_active", "is_pinned", "is_featured")
    list_editable = ("price", "is_active", "is_featured")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")
    fieldsets = (
        (None, {
            "fields": ("region", "name", "slug", "zone", "price", "is_active"),
        }),
        ("Display & Ordering", {
            "fields": ("is_pinned", "is_featured", "sort_order"),
        }),
        ("Carousel", {
            "fields": ("carousel_image",),
        }),
        ("SEO", {
            "fields": ("meta_title", "meta_description"),
            "classes": ("collapse",),
        }),
    )
