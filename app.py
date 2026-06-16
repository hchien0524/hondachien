import streamlit as st
import yfinance as yf
import pandas as pd
import time
import twstock  # 載入台股專屬神級套件

st.set_page_config(page_title="HIOS 波段雷達", layout="wide")
st.title("🚀 HIOS 波段雷達 (全市場解鎖 V3.0)")

# --- 獲取全市場代號與名稱 (使用 twstock 離線資料庫，破解防火牆) ---
@st.cache_data
def get_market_data(market_type):
    tickers = []
    names = {}
    target_market = "上市" if market_type == "上市 (TWSE) 約900檔" else "上櫃"
    
    for code, info in twstock.codes.items():
        if info.type == '股票' and info.market == target_market:
            # 排除權證、ETF等，只抓純股票 (通常代號是4碼)
            if len(code) == 4:
                suffix = ".TW" if target_market == "上市" else ".TWO"
                tickers.append(f"{code}{suffix}")
                names[code] = info.name
    return tickers, names

# --- 側邊欄 UI ---
st.sidebar.header("⚙️ 掃描範圍與參數")
scan_mode = st.sidebar.radio(
    "請選擇掃描範圍：",
    ("自選股 (快速)", "上市 (TWSE) 約900檔", "上櫃 (TPEx) 約800檔")
)

tickers_input = ""
if scan_mode == "自選股 (快速)":
    tickers_input = st.sidebar.text_area("請輸入自選股代號 (逗號分隔)", "2382, 3413, 3015, 8210, 2421, 6274")
else:
    st.sidebar.info(f"⚠️ 警告：全市場掃描約需 7-10 分鐘，請保持網頁開啟勿關閉。")

st.sidebar.markdown("---")
a_ma20_bias = st.sidebar.slider("A策略 MA20 正乖離上限 (%)", 1.0, 15.0, 5.0)
b_ma60_bias = st.sidebar.slider("B策略 MA60 正乖離上限 (%)", 1.0, 20.0, 10.0)
b_vol_min = st.sidebar.slider("B策略 成交量門檻 (張)", 500, 10000, 3000)

# --- 核心邏輯 ---
if st.sidebar.button("🚀 啟動掃描"):
    target_tickers = []
    stock_names_dict = {}

    if scan_mode == "自選股 (快速)":
        raw_tickers = [t.strip() for t in tickers_input.split(",")]
        for t in raw_tickers:
            pure_code = t.replace('.TW', '').replace('.TWO', '')
            # 嘗試從 twstock 抓名稱與正確的上市櫃後綴
            if pure_code in twstock.codes:
                stock_names_dict[pure_code] = twstock.codes[pure_code].name
                market = twstock.codes[pure_code].market
                suffix = ".TW" if market == "上市" else ".TWO"
                target_tickers.append(f"{pure_code}{suffix}")
            else:
                target_tickers.append(f"{pure_code}.TW") # 預設
    else:
        target_tickers, stock_names_dict = get_market_data(scan_mode)

    if not target_tickers:
        st.error("無法取得股票名單，請稍後再試。")
        st.stop()

    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_stocks = len(target_tickers)

    for i, ticker in enumerate(target_tickers):
        pure_code = ticker.replace('.TW', '').replace('.TWO', '')
        current_name = stock_names_dict.get(pure_code, "未知")
        status_text.text(f"正在掃描 {ticker} {current_name} ... ({i+1}/{total_stocks})")
        
        try:
            df = yf.download(ticker, period="6mo", progress=False)
            
            if df.empty or len(df) < 60:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA60'] = df['Close'].rolling(window=60).mean()
            df['Volume_張'] = df['Volume'] / 1000
            df['Volume_MA5'] = df['Volume_張'].rolling(window=5).mean()

            latest = df.iloc[-1]
            close_price = float(latest['Close'])
            ma20 = float(latest['MA20'])
            ma60 = float(latest['MA60'])
            vol_today = float(latest['Volume_張'])
            vol_ma5 = float(latest['Volume_MA5'])

            if pd.isna(ma20) or pd.isna(ma60):
                continue

            a_cond = (close_price > ma20) and (((close_price - ma20) / ma20 * 100) < a_ma20_bias)
            b_cond = (vol_today > vol_ma5) and (vol_today > b_vol_min) and (((close_price - ma60) / ma60 * 100) < b_ma60_bias)

            if a_cond or b_cond:
                buy_zone = f"{ma20:.1f} ~ {ma20 * 1.02:.1f}"
                stop_loss = ma20 * 0.97
                target = close_price * 1.15
                status = "🟢 可佈局" if close_price <= (ma20 * 1.02) else "🟡 觀察等待"
                warning = "⚠️ 爆量/隔日沖風險" if vol_today > (vol_ma5 * 3) else ""
                
                strategy = []
                if a_cond: strategy.append("A策略")
                if b_cond: strategy.append("B策略")

                results.append({
                    "代號": pure_code,
                    "名稱": current_name,
                    "收盤價": round(close_price, 1),
                    "符合策略": "+".join(strategy),
                    "MA20乖離(%)": round((close_price - ma20) / ma20 * 100, 1),
                    "成交量(張)": int(vol_today),
                    "建議買區": buy_zone,
                    "停損價": round(stop_loss, 1),
                    "目標價": round(target, 1),
                    "狀態": status,
                    "警示": warning
                })
                
        except Exception as e:
            pass 
            
        time.sleep(0.2) 
        progress_bar.progress((i + 1) / total_stocks)

    status_text.text(f"掃描完成！共找出 {len(results)} 檔符合條件的標的。")
    
    if results:
        st.dataframe(pd.DataFrame(results), use_container_width=True)
    else:
        st.info("目前沒有符合條件的標的。")
