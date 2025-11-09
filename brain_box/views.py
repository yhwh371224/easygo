from decimal import Decimal
from django.shortcuts import render, redirect
from .models import TradeCalculation
from .utils import calc_stock_profit, calc_profit_rate, calc_percent_price
from django.contrib.auth.decorators import login_required


@login_required
def calculate_trade(request):
    if request.method == "POST":
        action = request.POST.get('action')

        # --- ① 계산만 수행 (DB 저장 안 함) ---
        if action == "calc_trade":
            buy_price = Decimal(request.POST['buy_price'])
            sell_price = Decimal(request.POST['sell_price'])
            quantity = Decimal(request.POST['quantity'])
            trade_type = request.POST['trade_type']

            gross_profit, net_profit, total_fee = calc_stock_profit(buy_price, sell_price, quantity, trade_type)
            gross_rate, net_rate = calc_profit_rate(buy_price, sell_price, trade_type)

            # result.html 로 계산결과만 전달 (저장 X)
            context = {
                'buy_price': round(buy_price, 4),
                'sell_price': round(sell_price, 4),
                'quantity': int(quantity),
                'trade_type': trade_type,
                'gross_profit': round(gross_profit, 2),
                'total_fee': round(total_fee, 2),
                'net_profit': round(net_profit, 2),
                'gross_rate': round(gross_rate, 2),
                'net_rate': round(net_rate, 2),
            }
            return render(request, 'brain_box/result.html', context)

        # --- ② Save 버튼 눌렀을 때 DB에 저장 ---
        elif action == "save_trade":
            buy_price = Decimal(request.POST['buy_price'])
            sell_price = Decimal(request.POST['sell_price'])
            quantity = int(request.POST['quantity'])
            trade_type = request.POST['trade_type']
            gross_profit = Decimal(request.POST['gross_profit'])
            net_profit = Decimal(request.POST['net_profit'])
            total_fee = Decimal(request.POST['total_fee'])
            gross_rate = Decimal(request.POST['gross_rate'])
            net_rate = Decimal(request.POST['net_rate'])

            TradeCalculation.objects.create(
                buy_price=buy_price,
                sell_price=sell_price,
                quantity=quantity,
                trade_type=trade_type,
                gross_profit=gross_profit,
                total_fee=total_fee,
                net_profit=net_profit,
                gross_rate=gross_rate,
                net_rate=net_rate,
            )

            return render(request, 'brain_box/saved.html', {'trade_type': trade_type})

        # --- ③ 퍼센트 계산 부분 ---
        elif action == "calc_percent":
            base_price = Decimal(request.POST['base_price'])
            percent = Decimal(request.POST['percent'])
            quantity = Decimal(request.POST.get('quantity', 1))
            trade_type = request.POST['trade_type']

            result_price = calc_percent_price(base_price, percent, trade_type)
            if trade_type == "Short":
                result_total = base_price - result_price
            else:
                result_total = result_price - base_price

            return render(request, 'brain_box/percent_calc.html', {
                'base_price': base_price,
                'percent': percent,
                'trade_type': trade_type,
                'result_price': round(result_price, 4),
                'result_total': round(result_total, 4),
                'quantity': quantity
            })

    return render(request, 'brain_box/form.html')
