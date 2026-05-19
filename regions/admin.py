from django.contrib import admin

from .models import (
    Country,
    Region,
    RegionSuburb,
    Airport,
    Terminal,
    TerminalPickupPoint,
    PickupPointMap,
    CruiseTerminal,
    VehicleType,
    SpecialItemType,
    PricingRule,
)


class PickupPointMapInline(admin.TabularInline):
    model = PickupPointMap
    extra = 1
    fields = ("type", "title", "url")


@admin.register(TerminalPickupPoint)
class TerminalPickupPointAdmin(admin.ModelAdmin):
    list_display = ("terminal", "name", "sort_order")
    list_filter = ("terminal__airport",)
    list_editable = ("sort_order",)
    inlines = [PickupPointMapInline]


class TerminalPickupPointInline(admin.StackedInline):
    model = TerminalPickupPoint
    extra = 1
    show_change_link = True
    fields = ("name", "sort_order", "instruction")


@admin.register(Terminal)
class TerminalAdmin(admin.ModelAdmin):
    list_display = ("airport", "name", "type", "icon", "sort_order")
    list_filter = ("airport",)
    list_editable = ("sort_order",)
    inlines = [TerminalPickupPointInline]
    fieldsets = (
        (None, {
            "fields": ("airport", "name", "type", "icon", "sort_order"),
        }),
        ("Tip / Note", {
            "fields": ("note",),
            "description": "Optional tip shown inside the terminal panel. Leave blank to hide.",
        }),
    )


class TerminalInline(admin.TabularInline):
    model = Terminal
    extra = 1
    show_change_link = True
    fields = ("name", "type", "icon", "sort_order")


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


_ZONE_HELP = (
    "<b>Melbourne:</b> Airport · Inner North/West · Central Melbourne · Inner North · "
    "Inner South · Inner East · Eastern Suburbs · Northern Suburbs · Western Suburbs · "
    "South-East · Regional<br>"
    "<b>Sydney:</b> sydney_city · inner_west · central_west · west · north_west · "
    "outer_west · upper_north_shore · north_shore · northern_beaches · eastern_suburbs<br>"
    "<b>Gold Coast:</b> Southern Beaches · Southern Gold Coast · Central Gold Coast · "
    "Northern Gold Coast · Outer Northern Gold Coast · Far Northern Fringe<br>"
    "<b>Brisbane:</b> Inner Brisbane · Inner South · Eastern · Northern · Southern · "
    "Western · North-West · Redlands"
)


@admin.register(RegionSuburb)
class RegionSuburbAdmin(admin.ModelAdmin):
    ordering = ("region", "-is_pinned", "-is_featured", "sort_order", "name")
    list_display = ("name", "region", "zone", "price", "is_active", "is_pinned", "is_featured")
    list_filter = ("region", "zone", "is_active", "is_pinned", "is_featured")
    list_editable = ("price", "is_active", "is_featured")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["zone"].help_text = _ZONE_HELP
        return form

    fieldsets = (
        (None, {
            "fields": ("region", "name", "slug", "zone", "price", "distance_km", "is_active"),
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


@admin.register(CruiseTerminal)
class CruiseTerminalAdmin(admin.ModelAdmin):
    list_display = ['name', 'region', 'distance_km', 'base_price', 'lat', 'lng']
    list_filter = ['region']
    list_editable = ['distance_km', 'base_price']


@admin.register(VehicleType)
class VehicleTypeAdmin(admin.ModelAdmin):
    list_display  = ("name", "slug", "capacity_pax", "price_multiplier", "is_active")
    list_editable = ("price_multiplier", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(SpecialItemType)
class SpecialItemTypeAdmin(admin.ModelAdmin):
    list_display  = ("name", "slug", "fee", "is_active")
    list_editable = ("fee", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(PricingRule)
class PricingRuleAdmin(admin.ModelAdmin):
    list_display = (
        "region", "rate_per_km", "extra_bag_fee", "oversize_fee",
        "second_stop_fee", "pax_surcharge_mid_fee", "pax_surcharge_large_fee",
    )
    fieldsets = (
        (None, {
            "fields": ("region",),
        }),
        ("Distance & Vehicle", {
            "fields": ("rate_per_km",),
        }),
        ("Extra Fees", {
            "fields": (
                "extra_bag_fee", "oversize_fee", "second_stop_fee",
                "special_item_fee", "special_item_oversize_fee",
            ),
        }),
        ("Passenger Surcharges", {
            "fields": ("pax_surcharge_mid_fee", "pax_surcharge_large_fee"),
            "description": "mid = 5–9 pax, large = 10+ pax (stacked on top of mid)",
        }),
        ("Peak / Night Windows", {
            "fields": ("peak_windows",),
            "description": (
                'JSON list. Example: '
                '[{"type":"peak","start":6,"end":9,"surcharge_rate":0.20}]'
            ),
        }),
    )