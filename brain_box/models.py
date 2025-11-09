from django.db import models
from decimal import Decimal

TRADE_TYPES = [
    ('Long', 'Long'),
    ('Short', 'Short'),
]

class TradeCalculation(models.Model):
    trade_type = models.CharField(max_length=10, choices=TRADE_TYPES)
    buy_price = models.DecimalField(max_digits=12, decimal_places=4)
    sell_price = models.DecimalField(max_digits=12, decimal_places=4)
    quantity = models.IntegerField()
    gross_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_fee = models.DecimalField(max_digits=12, decimal_places=2)
    net_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross_rate = models.DecimalField(max_digits=8, decimal_places=2)
    net_rate = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.trade_type} | Profit: {self.gross_profit}"

