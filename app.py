import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from openai import OpenAI

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

# ── 사이드바 ──────────────────────────────────────────────────
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
    st.header("🤖 AI 챗봇 설정")
    openai_api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="sk-...",
        help="OpenAI API 키를 입력하세요. 키는 서버에 저장되지 않습니다.",
    )
    st.markdown("---")
    st.caption("데이터 출처: Yahoo Finance")


# ── 데이터 수집 ───────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_stock_data(tickers, period: str):
    data = {}
    for name, ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            if not hist.empty:
                data[name] = {"history": hist, "ticker": ticker}
        except Exception:
            pass
    return data


if not selected_stocks:
    st.warning("하나 이상의 종목을 선택해주세요.")
    st.stop()

filtered_tickers = {k: v for k, v in STOCKS.items() if k in selected_stocks}

with st.spinner("데이터를 불러오는 중..."):
    stock_data = fetch_stock_data(tuple(filtered_tickers.items()), selected_period)


# ── 챗봇용 컨텍스트 생성 ──────────────────────────────────────
def build_stock_context(stock_data: dict, period_label: str) -> str:
    lines = [f"아래는 최근 {period_label} 기준 KOSPI 주요 종목의 주가 데이터입니다.\n"]
    for name, d in stock_data.items():
        hist = d["history"]
        current = hist["Close"].iloc[-1]
        prev = hist["Close"].iloc[-2] if len(hist) > 1 else current
        change_pct = (current - prev) / prev * 100
        high = hist["High"].max()
        low = hist["Low"].min()
        avg_vol = hist["Volume"].mean()
        lines.append(
            f"- {name}: 현재가 {current:,.0f}원 | 전일대비 {change_pct:+.2f}% | "
            f"기간최고 {high:,.0f}원 | 기간최저 {low:,.0f}원 | 평균거래량 {avg_vol:,.0f}"
        )
    return "\n".join(lines)


# ── 요약 카드 ──────────────────────────────────────────────────
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

    with cols[idx % 5]:
        arrow = "▲" if change >= 0 else "▼"
        st.metric(
            label=name,
            value=f"{current:,.0f}원",
            delta=f"{arrow} {abs(change):,.0f} ({change_pct:+.2f}%)",
            delta_color="normal" if change >= 0 else "inverse",
        )

st.markdown("---")

# ── 주가 차트 ──────────────────────────────────────────────────
st.subheader("📉 주가 추이")

tab1, tab2 = st.tabs(["라인 차트", "캔들 차트"])

with tab1:
    fig_line = go.Figure()
    for name in selected_stocks:
        if name not in stock_data:
            continue
        hist = stock_data[name]["history"]
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
        go.Bar(x=hist.index, y=hist["Volume"], name=name, opacity=0.7)
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
    current = hist["Close"].iloc[-1]
    prev = hist["Close"].iloc[-2] if len(hist) > 1 else current
    change_pct = (current - prev) / prev * 100
    rows.append(
        {
            "종목명": name,
            "현재가 (원)": f"{current:,.0f}",
            "전일 대비 (%)": f"{change_pct:+.2f}%",
            "기간 최고가": f"{hist['High'].max():,.0f}",
            "기간 최저가": f"{hist['Low'].min():,.0f}",
            "평균 거래량": f"{hist['Volume'].mean():,.0f}",
        }
    )

if rows:
    st.dataframe(pd.DataFrame(rows).set_index("종목명"), use_container_width=True)

st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 캐시 유효: 5분")

st.markdown("---")

# ── AI 챗봇 ──────────────────────────────────────────────────
st.subheader("🤖 AI 주식 챗봇")

if not openai_api_key:
    st.info("왼쪽 사이드바에 OpenAI API Key를 입력하면 챗봇을 사용할 수 있습니다.")
else:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    stock_context = build_stock_context(stock_data, selected_period_label)

    # 대화 내역 출력
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("주식에 대해 질문하세요. 예) 삼성전자 최근 흐름 어때?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("답변 생성 중..."):
                try:
                    client = OpenAI(api_key=openai_api_key)
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "당신은 한국 주식 전문가 AI입니다. "
                                    "아래 실시간 주가 데이터를 기반으로 사용자 질문에 답변하세요. "
                                    "투자 권유는 하지 말고, 데이터 기반의 객관적인 분석만 제공하세요.\n\n"
                                    + stock_context
                                ),
                            },
                            *st.session_state.messages,
                        ],
                        temperature=0.7,
                    )
                    answer = response.choices[0].message.content
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                except Exception as e:
                    st.error(f"오류 발생: {e}")

    if st.session_state.get("messages"):
        if st.button("대화 초기화"):
            st.session_state.messages = []
            st.rerun()
