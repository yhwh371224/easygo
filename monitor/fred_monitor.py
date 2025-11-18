from datetime import datetime, timedelta
import statistics
from fredapi import Fred
from django.conf import settings
from basecamp.utils import handle_email_sending
from monitor.config import FRED_API_KEY

# -------------------------------
# FRED API
# -------------------------------
fred = Fred(api_key=FRED_API_KEY)

# -------------------------------
# 감시할 지표
# -------------------------------
SERIES = {
    "SOFR": "SOFR30DAYAVG",
    "RRP": "RRPONTSYD",
    "RRP_AR": "RRPONTSYAWARD",
    "TGA": "WTREGEN",
    "10Y_Treasury": "DGS10",
    "USD_Index": "DTWEXBGS",
}

# -------------------------------
# ALERT CONFIG
# -------------------------------
ALERT_CONFIG = {}
COMMON_NAMES = ["SOFR", "RRP", "RRP_AR", "10Y_Treasury", "USD_Index"]

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
    "SOFR": "단기 은행간 달러 금리: Repo 시장 금리 변동에 민감",
    "RRP": "연준 역환매(RRP) 잔액: 은행이 안전자산으로 이동",
    "RRP_AR": "RRP 수수료율: 단기 자금시장 압력 신호",
    "TGA": "재무부 계정 잔액: 유동성 흡수/공급 신호",
    "10Y_Treasury": "미국 10년물 국채 금리: 장기 금리 벤치마크",
    "USD_Index": "미국 달러 지수: 주요통화대비 달러강도",
    "⚠️": "위험신호, 상: 상단 임계값 초과, 하: 하단 임계값 미달", 
    "✅": "정상범위, 걱정할 단계는 아니다."
}

# -------------------------------
# FRED 데이터 가져오기
# -------------------------------
def fetch_history(series_id, days):
    end = datetime.today()
    # 최소 20일 윈도우라면 최소 30~40일치 데이터를 가져오는 것이 안전
    start = end - timedelta(days=max(days*2, 50))
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

            # Add the table row
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
    results = run_all_alerts(data)
    prioritized = prioritize_signals(results)
    alerts = generate_alert_messages_grouped(data)

    # HTML 테이블 생성
    html_rows = "".join(alerts)

    # 지표 설명
    indicators_html = ""
    for name, desc in INDICATOR_MEANING.items():
        indicators_html += f"""
        <p style='font-size:11px; line-height:1.2; font-style:italic; margin:2px 0;'>
            {name}: {desc}
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
        }
    )
