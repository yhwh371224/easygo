from datetime import datetime, timedelta
import statistics
from fredapi import Fred
from django.conf import settings
from basecamp.utils import handle_email_sending
from monitor.config import FRED_API_KEY

# FRED API
fred = Fred(api_key=FRED_API_KEY)

# 감시할 지표
SERIES = {
    "SOFR": "SOFR30DAYAVG",
    "RRP": "RRPONTSYD",
    "RRP_AwardRate": "RRPONTSYAWARD",
    "TGA": "WTREGEN",
    "10Y_Treasury": "DGS10",
}

# 알람 설정
ALERT_CONFIG = {
    "SOFR": {"window": 20, "sigma_threshold": 2},
    "RRP": {"window": 20, "sigma_threshold": 2},
    "RRP_AwardRate": {"window": 20, "sigma_threshold": 2},
    "TGA": {"window": 20, "sigma_threshold": 2},
    "10Y_Treasury": {"window": 20, "sigma_threshold": 2},
}

# 지표 설명
INDICATOR_MEANING = {
    "SOFR": "단기 은행간 달러 금리: Repo 시장 금리 변동에 민감",
    "RRP": "연준 역환매(RRP) 잔액: 은행이 안전자산으로 이동",
    "RRP_AwardRate": "RRP 수수료율: 단기 자금시장 압력 신호",
    "TGA": "재무부 계정 잔액: 유동성 흡수/공급 신호",
    "10Y_Treasury": "미국 10년물 국채 금리: 장기 금리 벤치마크",
}

def fetch_history(series_id, days):
    end = datetime.today()
    start = end - timedelta(days=days*2)
    data = fred.get_series(series_id, observation_start=start, observation_end=end)
    return data.dropna()

def check_and_alert(request=None):
    alert_lines = []

    for name, series_id in SERIES.items():
        conf = ALERT_CONFIG[name]
        hist = fetch_history(series_id, conf["window"])

        if len(hist) == 0:
            latest = mean = upper = lower = None
            status = "데이터 없음"
        elif len(hist) < conf["window"]:
            latest = hist.iloc[-1]
            mean = upper = lower = None
            status = "데이터 부족"
        else:
            latest = hist.iloc[-1]
            mean = statistics.mean(hist)
            stdev = statistics.stdev(hist)
            upper = mean + conf["sigma_threshold"] * stdev
            lower = mean - conf["sigma_threshold"] * stdev

            if latest > upper:
                status = "⚠️ 경고: 상단 임계값 초과"
            elif latest < lower:
                status = "⚠️ 경고: 하단 임계값 미달"
            else:
                status = "✅ 정상 범위"


    # HTML 테이블 생성
    html_rows = ""
    for row in alert_lines:
        latest = f"{row['latest']:.2f}" if row['latest'] is not None else '-'
        mean = f"{row['mean']:.2f}" if row['mean'] is not None else '-'
        upper = f"{row['upper']:.2f}" if row['upper'] is not None else '-'
        lower = f"{row['lower']:.2f}" if row['lower'] is not None else '-'

        html_rows += f"""
        <tr>
            <td>{row['name']}</td>
            <td>{latest}</td>
            <td>{row['status']}</td>
            <td>{mean}</td>
            <td>{upper}</td>
            <td>{lower}</td>
        </tr>
        """

    subject = f"[Liquidity Monitor] Status Update ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
    handle_email_sending(
        request=request,
        email=settings.DEFAULT_FROM_EMAIL,
        subject=subject,
        template_name="alert_template.html",
        context={"alerts_html": html_rows}
    )
