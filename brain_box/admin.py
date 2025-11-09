from django.contrib import admin
from easygo_review.admin import admin_site
from .models import TradeCalculation

@admin.register(TradeCalculation)
class TradeCalculationAdmin(admin.ModelAdmin):
    list_display = ('trade_type', 'buy_price', 'sell_price', 'quantity', 'gross_profit', 'net_profit', 'gross_rate', 'net_rate', 'created_at')
    list_filter = ('trade_type', 'created_at')
    search_fields = ('trade_type',)
    ordering = ('-created_at',)


# 커스텀 AdminSite에도 등록
admin_site.register(TradeCalculation, TradeCalculationAdmin)

# 기본 admin.site에는 이미 등록되어 있는지 확인 후 등록
if not admin.site.is_registered(TradeCalculation):
    admin.site.register(TradeCalculation, TradeCalculationAdmin)