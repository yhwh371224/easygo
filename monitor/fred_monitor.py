from datetime import datetime, timedelta
import statistics
from fredapi import Fred
from django.conf import settings
from basecamp.utils import handle_email_sending
from decouple import config

# -------------------------------
# FRED API
# -------------------------------
FRED_API_KEY = config('FRED_API_KEY')

# fred 객체 생성
fred = Fred(api_key=FRED_API_KEY)

# -------------------------------
# 감시할 지표
# -------------------------------
SERIES = {
    "SOFR": "SOFR30DAYAVG",
    "SRF": "SRFTSYD",
    "RRP": "RRPONTSYD",
    "TGA": "WTREGEN",
    "10Y_Treasury": "DGS10",
    "USD_Index": "DTWEXBGS",
}

# -------------------------------
# ALERT CONFIG
# -------------------------------
ALERT_CONFIG = {}
COMMON_NAMES = ["SOFR", "SRF", "RRP", "10Y_Treasury", "USD_Index"]

# 3일, 5일, 20일
for name in COMMON_NAMES:
    for window in [3, 5, 20]:
        ALERT_CONFIG[f"{name}_{window}"] = {"window": window, "sigma_threshold": 2}

# TGA는 단기만
for window in [3, 5]:
    ALERT_CONFIG[f"TGA_{window}"] = {"window": window, "sigma_threshold": 2}

# -------------------------------
# 지표 설명
# -------------------------------
INDICATOR_MEANING = {
    "SOFR": "(Secure Overnight Finaning Rate) 은행간 달러 금리: 금리가 낮으면 일반적으로 단기 유동성이 충분하다는 신호지만, 안전자산(국채) 수요 급증으로 낮아질 때는 오히려 스트레스 상황일 수 있슴",
    "SRF": "(Standing Repo Facility) 은행이 맡긴 국채를 담보로 연준이 돈을 단기로 빌려줄 때 금리. 이 금리가 낮으면 연준에서 자금을 싸게 조달할 수 있어 유동성이 늘고, 금리가 높으면 조달비용 상승으로 유동성 축소.",
    "RRP": "(Reverse Repurchase Agreement) 은행, MMF 기관이 여유자금을 연준에 맡기고 국채를 받는 거래 규모. RRP 수치가 높으면 자금이 시장에서 빠져 연준으로 이동한 것이므로 유동성 감소, 잔액이 낮으면 시장으로 자금이 풀린 상태라 유동성 증가로 해석.",
    "TGA": "Treasury General Account. 수치가 높다는 것은 돈이 구좌에 많다는 것이므로 재무부가 돈을 풀지 않고 있다는 것. 상대적으로 시장엔 유동성이 낮다는 것으로 볼 수 있슴. 단, 잔액 증가는 세수 유입이나 국채 발행 증가로도 발생할 수 있음", 
    "10Y_Treasury": "미국 10년물 국채 금리: 국채금리가 높으면 돈과 자산이 국채쪽으로 몰리게 된다 그러므로 시장엔 유동성이 좋지 않고 국채금리가 낮으면 유동성이 좋아진다.",
    "USD_Index": "미국 달러 지수: 달러 지수가 높으면 유동성이 좋지 않게된다. 모든 자산이 달러 사재기로 향하여 시장엔 유동성이 줄어든다",
    "⚠️": "위험신호, 평균치보다 높거나 낮을 때를 말하는 것. 평균치에서 멀어질수록 위험증가", 
    "✅": "정상범위, 걱정할 단계는 아니다.",
    "!": "지표별로 3일, 5일, 20일 윈도우로 각각 계산된 Z-score를 기준으로 우선순위를 매김. 3일 윈도우가 가장 민감하게 반응하므로 우선순위 1, 5일이 2, 20일이 3임. 동일 우선순위 내에서는 Z-score 절대값이 큰 순서대로 정렬. (위 수치를 매일 확인하면서 유동성 흐름을 예측하는 것이 중요하다)",
}

# -------------------------------
# FRED 데이터 가져오기
# -------------------------------
def fetch_history(series_id, days):
    end = datetime.today()
    # 최소 20일 윈도우라면 최소 30~40일치 데이터를 가져오는 것이 안전
    start = end - timedelta(days=max(days*2, 40))
    data = fred.get_series(series_id, observation_start=start, observation_end=end)
    return data.dropna()

# -------------------------------
# Z-score 기반 시그널 계산
# -------------------------------
def compute_alert_signal(series, window, sigma_threshold):
    if len(series) < window:
        return None
    rolling = series[-window:]
    mean = statistics.mean(rolling)
    stdev = statistics.stdev(rolling)
    if stdev == 0:
        return None
    zscore = (series.iloc[-1] - mean) / stdev
    if abs(zscore) >= sigma_threshold:
        return zscore
    return None

# -------------------------------
# 모든 지표 계산
# -------------------------------
def run_all_alerts(data):
    results = {}
    for key, config in ALERT_CONFIG.items():
        base_name = key.rsplit("_", 1)[0]
        if base_name not in data:
            continue
        z = compute_alert_signal(
            series=data[base_name],
            window=config["window"],
            sigma_threshold=config["sigma_threshold"]
        )
        # Record Z-score even if it didn't exceed threshold
        results[key] = z if z is not None else 0
    return results

# -------------------------------
# 우선순위 정렬: 3일 > 5일 > 20일
# -------------------------------
def prioritize_signals(results):
    priority = {}
    for key, z in results.items():
        if key.endswith("_3"):
            p = 1
        elif key.endswith("_5"):
            p = 2
        else:
            p = 3
        priority[key] = (p, z)
    return dict(sorted(priority.items(), key=lambda x: (x[1][0], -abs(x[1][1]))))


# -------------------------------
# HTML alert 메시지 생성 (그룹별)
# -------------------------------
def generate_alert_messages_grouped(data):
    messages = []

    # Group by indicator
    for name in SERIES.keys():
        windows = [w for w in [3, 5, 20] if f"{name}_{w}" in ALERT_CONFIG]
        first = True  # to use rowspan
        for window in windows:
            key = f"{name}_{window}"
            latest = data[name].iloc[-1]
            rolling = data[name][-ALERT_CONFIG[key]['window']:]
            mean_val = statistics.mean(rolling)
            stdev_val = statistics.stdev(rolling) if len(rolling) > 1 else 0
            upper = mean_val + ALERT_CONFIG[key]['sigma_threshold'] * stdev_val
            lower = mean_val - ALERT_CONFIG[key]['sigma_threshold'] * stdev_val

            # Compute Z-score
            z = compute_alert_signal(data[name], window, ALERT_CONFIG[key]['sigma_threshold'])
            status = "⚠️" if z is not None and abs(z) >= ALERT_CONFIG[key]['sigma_threshold'] else "✅"

            # Format numbers
            if name == "TGA":
                latest_fmt = f"{latest:,.0f}"
                mean_fmt = f"{mean_val:,.0f}"
                upper_fmt = f"{upper:,.0f}"
                lower_fmt = f"{lower:,.0f}"
            else:
                latest_fmt = f"{latest:.2f}"
                mean_fmt = f"{mean_val:.2f}"
                upper_fmt = f"{upper:.2f}"
                lower_fmt = f"{lower:.2f}"

            # Add the table row. 
            if first:
                messages.append(
                    f"<tr>"
                    f"<td rowspan='{len(windows)}'>{name}</td>"
                    f"<td>{window}일</td>"
                    f"<td>{latest_fmt}</td>"
                    f"<td>{status}</td>"
                    f"<td>{mean_fmt}</td>"
                    f"<td>{upper_fmt}</td>"
                    f"<td>{lower_fmt}</td>"
                    f"</tr>"
                )
                first = False
            else:
                messages.append(
                    f"<tr>"
                    f"<td>{window}일</td>"
                    f"<td>{latest_fmt}</td>"
                    f"<td>{status}</td>"
                    f"<td>{mean_fmt}</td>"
                    f"<td>{upper_fmt}</td>"
                    f"<td>{lower_fmt}</td>"
                    f"</tr>"
                )

        # Add a separator row for spacing
        messages.append(
            "<tr style='height:10px;'><td colspan='7'></td></tr>"
        )

    return messages

# -------------------------------
# 메인 함수: 이메일 발송
# -------------------------------
def check_and_alert(request=None):
    # FRED 데이터 가져오기
    data = {}
    for name, series_id in SERIES.items():
        data[name] = fetch_history(series_id, 20)

    # 알람 계산
    alerts = generate_alert_messages_grouped(data)

    # HTML 테이블 생성
    html_rows = "".join(alerts)

    # 지표 설명
    indicators_html = ""
    for name, desc in INDICATOR_MEANING.items():
        indicators_html += f"""
        <p style='font-size:11px; line-height:1.2; font-style:italic; margin:2px 0;'>
            <strong>{name}</strong>: {desc}<br>
        </p>
        """

    # 이메일 발송
    subject = f"[Liquidity Monitor] Status Update ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
    handle_email_sending(
        request=request,
        email=settings.DEFAULT_FROM_EMAIL,
        subject=subject,
        template_name="alert_template.html",
        context={
            "alerts_html": html_rows,
            "indicators_html": indicators_html,
        },
        email1="gwillbd@gmail.com"
    )
