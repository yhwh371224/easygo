from datetime import datetime, timedelta
import statistics
from fredapi import Fred
from django.conf import settings
from basecamp.utils import handle_email_sending
from monitor.config import FRED_API_KEY

fred = Fred(api_key=FRED_API_KEY)

# 감시할 지표
SERIES = {
    "SOFR": "SOFR30DAYAVG",
    "RRP": "RRPONTSYD",
    "RRP_AwardRate": "RRPONTSYAWARD", 
    "TGA": "WTREGEN",
}

# 알림 설정
ALERT_CONFIG = {
    "SOFR": {"window": 20, "sigma_threshold": 2, "description": "SOFR spike detected"},
    "RRP": {"window": 20, "sigma_threshold": 2, "description": "RRP abnormal move"},
    "RRP_AwardRate": {"window": 20, "sigma_threshold": 2, "description": "RRP award rate abnormal"},
    "TGA": {"window": 20, "sigma_threshold": 2, "description": "TGA liquidity swing"},
}

# 지표 의미 설명 (상세)
INDICATOR_MEANING = {
    "SOFR": "단기 은행간 달러 금리: 급등 시 은행 간 유동성 긴축 신호, Repo 시장 금리 변동에 민감",
    "RRP": "연준 역환매(RRP) 잔액: 급증 시 은행이 안전자산으로 현금을 이동시키는 신호",
    "RRP_AwardRate": "연준 RRP 수수료율: 급등 시 단기 자금 시장 압박과 유동성 긴축을 의미",
    "TGA": "재무부 계정 잔액: 갑작스런 증가/감소는 은행 시스템 유동성 흡수/공급 신호",
}

def fetch_history(series_id, days):
    end = datetime.today()
    start = end - timedelta(days=days*2)
    data = fred.get_series(series_id, observation_start=start, observation_end=end)
    return data.dropna()

def check_and_alert(request=None):
    alerts = []

    for name, series_id in SERIES.items():
        conf = ALERT_CONFIG.get(name)
        if not conf:
            continue  # ALERT_CONFIG에 정의되지 않은 지표는 건너뜀

        hist = fetch_history(series_id, conf["window"])
        if len(hist) < conf["window"]:
            continue

        latest = hist.iloc[-1]
        mean = statistics.mean(hist)
        stdev = statistics.stdev(hist)
        upper = mean + conf["sigma_threshold"] * stdev
        lower = mean - conf["sigma_threshold"] * stdev

        if latest > upper:
            alerts.append(f"<b>{name}</b>: {latest:.4f} > upper threshold ({upper:.4f})<br>설명: {INDICATOR_MEANING[name]}")
        elif latest < lower:
            alerts.append(f"<b>{name}</b>: {latest:.4f} < lower threshold ({lower:.4f})<br>설명: {INDICATOR_MEANING[name]}")

    if alerts:
        subject = f"[ALERT] Liquidity Indicator Warning ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
        html_content = "<br>".join(alerts)

        handle_email_sending(
            request=request,
            email=settings.DEFAULT_FROM_EMAIL,
            subject=subject,
            template_name="alert_template.html",
            context={"alerts_html": html_content}
        )
