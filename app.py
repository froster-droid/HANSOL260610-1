import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(
    page_title="국내 주식 대시보드",
    page_icon="📈",
    layout="wide",
)

STOCKS = {
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "LG에너지솔루션": "373220.KS",
    "삼성바이오로직스": "207940.KS",
    "현대차": "005380.KS",
    "NAVER": "035420.KS",
    "카카오": "035720.KS",
    "셀트리온": "068270.KS",
    "POSCO홀딩스": "005490.KS",
    "기아": "000270.KS",
}

st.title("📈 국내 주식 대시보드")
st.markdown("KOSPI 주요 종목 10개의 실시간 데이터를 제공합니다.")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    period_map = {
        "1개월": "1mo",
        "3개월": "3mo",
        "6개월": "6mo",
        "1년": "1y",
        "2년": "2y",
    }
    selected_period_label = st.selectbox("조회 기간", list(period_map.keys()), index=2)
    selected_period = period_map[selected_period_label]

    selected_stocks = st.multiselect(
        "종목 선택",
        list(STOCKS.keys()),
        default=list(STOCKS.keys()),
    )
    st.markdown("---")
    st.caption("데이터 출처: Yahoo Finance")


@st.cache_data(ttl=300)
def fetch_stock_data(tickers: dict, period: str):
    data = {}
    for name, ticker in tickers.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            info = stock.fast_info
            if not hist.empty:
                data[name] = {"history": hist, "info": info, "ticker": ticker}
        except Exception:
            pass
    return data


if not selected_stocks:
    st.warning("하나 이상의 종목을 선택해주세요.")
    st.stop()

filtered_tickers = {k: v for k, v in STOCKS.items() if k in selected_stocks}

with st.spinner("데이터를 불러오는 중..."):
    stock_data = fetch_stock_data(tuple(filtered_tickers.items()), selected_period)

# ── 요약 카드 ──────────────────────────────────────────────
st.subheader("📊 종목 요약")

cols = st.columns(5)
for idx, name in enumerate(selected_stocks):
    if name not in stock_data:
        continue
    hist = stock_data[name]["history"]
    current = hist["Close"].iloc[-1]
    prev = hist["Close"].iloc[-2] if len(hist) > 1 else current
    change = current - prev
    change_pct = (change / prev) * 100

    col = cols[idx % 5]
    with col:
        arrow = "▲" if change >= 0 else "▼"
        color = "normal" if change >= 0 else "inverse"
        st.metric(
            label=name,
            value=f"{current:,.0f}원",
            delta=f"{arrow} {abs(change):,.0f} ({change_pct:+.2f}%)",
            delta_color=color,
        )

st.markdown("---")

# ── 주가 차트 ──────────────────────────────────────────────
st.subheader("📉 주가 추이")

tab1, tab2 = st.tabs(["라인 차트", "캔들 차트"])

with tab1:
    fig_line = go.Figure()
    for name in selected_stocks:
        if name not in stock_data:
            continue
        hist = stock_data[name]["history"]
        # 기준값 대비 수익률(%) 표시
        base = hist["Close"].iloc[0]
        returns = (hist["Close"] / base - 1) * 100
        fig_line.add_trace(
            go.Scatter(
                x=hist.index,
                y=returns,
                name=name,
                mode="lines",
                hovertemplate="%{x}<br>수익률: %{y:.2f}%<extra>" + name + "</extra>",
            )
        )
    fig_line.update_layout(
        yaxis_title="수익률 (%)",
        xaxis_title="날짜",
        hovermode="x unified",
        height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig_line.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    st.plotly_chart(fig_line, use_container_width=True)

with tab2:
    candle_name = st.selectbox("캔들 차트 종목", selected_stocks, key="candle")
    if candle_name in stock_data:
        hist = stock_data[candle_name]["history"]
        fig_candle = go.Figure(
            go.Candlestick(
                x=hist.index,
                open=hist["Open"],
                high=hist["High"],
                low=hist["Low"],
                close=hist["Close"],
                name=candle_name,
            )
        )
        fig_candle.update_layout(
            yaxis_title="주가 (원)",
            xaxis_title="날짜",
            height=450,
            xaxis_rangeslider_visible=False,
        )
        st.plotly_chart(fig_candle, use_container_width=True)

st.markdown("---")

# ── 거래량 차트 ──────────────────────────────────────────────
st.subheader("📦 거래량")

fig_vol = go.Figure()
for name in selected_stocks:
    if name not in stock_data:
        continue
    hist = stock_data[name]["history"]
    fig_vol.add_trace(
        go.Bar(
            x=hist.index,
            y=hist["Volume"],
            name=name,
            opacity=0.7,
        )
    )
fig_vol.update_layout(
    barmode="group",
    yaxis_title="거래량",
    xaxis_title="날짜",
    height=350,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig_vol, use_container_width=True)

st.markdown("---")

# ── 상관관계 히트맵 ──────────────────────────────────────────
st.subheader("🔗 종목 간 수익률 상관관계")

if len(selected_stocks) >= 2:
    close_df = pd.DataFrame(
        {
            name: stock_data[name]["history"]["Close"]
            for name in selected_stocks
            if name in stock_data
        }
    )
    corr = close_df.pct_change().corr()
    fig_heat = px.imshow(
        corr,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        height=420,
    )
    fig_heat.update_layout(coloraxis_colorbar_title="상관계수")
    st.plotly_chart(fig_heat, use_container_width=True)
else:
    st.info("상관관계 분석을 위해 2개 이상의 종목을 선택해주세요.")

st.markdown("---")

# ── 상세 데이터 테이블 ──────────────────────────────────────
st.subheader("📋 종목별 상세 정보")

rows = []
for name in selected_stocks:
    if name not in stock_data:
        continue
    hist = stock_data[name]["history"]
    info = stock_data[name]["info"]
    current = hist["Close"].iloc[-1]
    prev = hist["Close"].iloc[-2] if len(hist) > 1 else current
    high_52w = hist["High"].max()
    low_52w = hist["Low"].min()
    avg_vol = hist["Volume"].mean()
    change_pct = (current - prev) / prev * 100

    rows.append(
        {
            "종목명": name,
            "현재가 (원)": f"{current:,.0f}",
            "전일 대비 (%)": f"{change_pct:+.2f}%",
            f"기간 최고가": f"{high_52w:,.0f}",
            f"기간 최저가": f"{low_52w:,.0f}",
            "평균 거래량": f"{avg_vol:,.0f}",
        }
    )

if rows:
    df_summary = pd.DataFrame(rows).set_index("종목명")
    st.dataframe(df_summary, use_container_width=True)

st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 캐시 유효: 5분")
