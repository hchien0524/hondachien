import streamlit as st
import yfinance as yf
import pandas as pd
import time
import requests

st.set_page_config(page_title="HIOS 波段雷達", layout="wide")
st.title("🚀 HIOS 波段雷達 (全市場解鎖 V2.0)")

# --- 專屬股票翻譯字典 (保留常用股，全市場名稱將由 API 盡量補齊) ---
STOCK_NAMES = {
    "2382": "廣達", "3413": "京鼎", "3015": "全漢",
    "8210": "勤誠", "2421": "建準", "6274": "台燿"
}

# --- 獲取全市場代號函數 ---
@st.cache_data(ttl=86400) # 快取一天，避免重複抓取
def get_market_tickers(market_type):
    tickers = []
    try:
        if market_type == "上市 (TWSE)":
            url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
            res = requests.get(url )
            data = res.json()
            tickers = [f"{item['Code']}.TW" for item in data if len(item['Code']) == 4] # 只抓4碼一般股票
        elif market_type == "上櫃 (TPEx)":
            url = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
            res = requests.get(url )
            data = res.json()
            tickers = [f"{item['SecuritiesCompanyCode']}.TWO" for item in data if len(item['SecuritiesCompanyCode']) == 4]
    except Exception as e:
        st.error(f"獲取市場代號失敗: {e}")
    return tickers

# --- 側邊欄 UI ---
st.sidebar.header("⚙️ 掃描範圍與參數")

# 新增：掃描模式選擇
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
    # 決定掃描名單
    if scan_mode == "自選股 (快速)":
        raw_tickers = [t.strip() for t in tickers_input.split(",")]
        # 自動補齊 .TW 或 .TWO (簡單判斷，若錯誤會在迴圈內修正)
        target_tickers = []
        for t in raw_tickers:
            if not t.endswith('.TW') and not t.endswith('.TWO'):
                target_tickers.append(f"{t}.TW") # 預設先加.TW
            else:
                target_tickers.append(t)
    else:
        target_tickers = get_market_tickers(scan_mode)

    if not target_tickers:
        st.error("無法取得股票名單，請稍後再試。")
        st.stop()

    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_stocks = len(target_tickers)

    for i, ticker in enumerate(target_tickers):
        status_text.text(f"正在掃描 {ticker} ... ({i+1}/{total_stocks})")
        
        try:
            df = yf.download(ticker, period="6mo", progress=False)
            
            # 如果是自選股且 .TW 抓不到，嘗試 .TWO
            if df.empty and scan_mode == "自選股 (快速)" and ticker.endswith('.TW'):
                ticker = ticker.replace('.TW', '.TWO')
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

                # 提取純數字代號
                pure_code = ticker.replace('.TW', '').replace('.TWO', '')
                stock_name = STOCK_NAMES.get(pure_code, "未知")

                results.append({
                    "代號": pure_code,
                    "名稱": stock_name,
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
            pass # 全市場掃描時，遇到錯誤直接默默跳過，不干擾畫面
            
        time.sleep(0.2) # 全市場掃描稍微加快一點點速度
        progress_bar.progress((i + 1) / total_stocks)

    status_text.text(f"掃描完成！共找出 {len(results)} 檔符合條件的標的。")
    
    if results:
        st.dataframe(pd.DataFrame(results), use_container_width=True)
    else:
        st.info("目前沒有符合條件的標的。")
