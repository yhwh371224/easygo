from decimal import Decimal

FEE_RATE = Decimal('0.001')  # 수수료 0.1%

def calc_stock_profit(buy_price, sell_price, quantity, trade_type, fee_rate=FEE_RATE):
    """
    순이익 계산
    Long → buy → sell
    Short → sell → buy
    """
    # 모든 값을 Decimal로 변환
    buy_price = Decimal(str(buy_price))
    sell_price = Decimal(str(sell_price))
    quantity = Decimal(str(quantity))
    
    buy_total = buy_price * quantity
    sell_total = sell_price * quantity
    total_fee = (buy_total + sell_total) * fee_rate

    if trade_type == 'Long':
        gross_profit = sell_total - buy_total
        net_profit = sell_total - buy_total - total_fee
    else:  # Short
        gross_profit = -(buy_total - sell_total)
        net_profit = -(buy_total - sell_total) - total_fee

    return gross_profit, net_profit, total_fee


def calc_profit_rate(buy_price, sell_price, trade_type, fee_rate=FEE_RATE):
    """
    수익률 계산: Gross rate와 Net rate(수수료 반영)
    """
    buy_price = Decimal(str(buy_price))
    sell_price = Decimal(str(sell_price))
    
    if trade_type == 'Long':
        gross_rate = (sell_price - buy_price) / buy_price * Decimal('100')
        net_rate = ((sell_price / buy_price) * (1 - fee_rate)**2 - 1) * Decimal('100')
    else:  # Short
        gross_rate = -(buy_price - sell_price) / buy_price * Decimal('100')
        net_rate = -(((buy_price / sell_price) * (1 - fee_rate)**2 - 1) * Decimal('100'))

    return gross_rate, net_rate


def calc_percent_price(base_price, percent, trade_type="Long"):
    """
    기준 가격 + 변동률 계산
    Short이면 변동률 방향 반대로 적용
    """
    base_price = Decimal(str(base_price))
    percent = Decimal(str(percent))
    if trade_type == "Short":
        percent = -percent
    return base_price * (Decimal('1') + percent / Decimal('100'))

