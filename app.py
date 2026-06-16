import streamlit as st
import yfinance as yf
import pandas as pd
import time

st.set_page_config(page_title="HIOS 波段雷達", layout="wide")
st.title("🚀 HIOS 波段雷達 (核心引擎 V1.0)")

# --- 側邊欄 UI ---
st.sidebar.header("⚙️ 參數設定")
tickers_input = st.sidebar.text_input("請輸入掃描名單 (逗號分隔)", "2382, 3413, 3015, 8210, 2421, 6274")
a_ma20_bias = st.sidebar.slider("A策略 MA20 正乖離上限 (%)", 1.0, 15.0, 5.0)
b_ma60_bias = st.sidebar.slider("B策略 MA60 正乖離上限 (%)", 1.0, 20.0, 10.0)
b_vol_min = st.sidebar.slider("B策略 成交量門檻 (張)", 500, 10000, 3000)

st.sidebar.subheader("🛡️ 進階濾網 (UI展示)")
st.sidebar.checkbox("啟用投信鎖碼濾網 (近5日買超>=3天)", value=True)
st.sidebar.checkbox("啟用融資洗盤濾網 (近5日融資減少)", value=False)

# --- 核心邏輯 ---
if st.sidebar.button("啟動全市場掃描"):
    raw_tickers = [t.strip() for t in tickers_input.split(",")]
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, ticker in enumerate(raw_tickers):
        status_text.text(f"正在抓取 {ticker} 資料...")
        
        try:
            # 自動判斷上市(.TW)或上櫃(.TWO)
            df = yf.download(f"{ticker}.TW", period="6mo", progress=False)
            if df.empty:
                df = yf.download(f"{ticker}.TWO", period="6mo", progress=False)
            
            if df.empty or len(df) < 60:
                st.warning(f"無法取得 {ticker} 資料，已跳過。")
                continue

            # 處理 yfinance 新版格式問題
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # 計算均線與成交量 (轉換為張)
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA60'] = df['Close'].rolling(window=60).mean()
            df['Volume_張'] = df['Volume'] / 1000
            df['Volume_MA5'] = df['Volume_張'].rolling(window=5).mean()

            # 取得最新一日資料
            latest = df.iloc[-1]
            close_price = float(latest['Close'])
            ma20 = float(latest['MA20'])
            ma60 = float(latest['MA60'])
            vol_today = float(latest['Volume_張'])
            vol_ma5 = float(latest['Volume_MA5'])

            if pd.isna(ma20) or pd.isna(ma60):
                continue

            # 策略判定
            a_cond = (close_price > ma20) and (((close_price - ma20) / ma20 * 100) < a_ma20_bias)
            b_cond = (vol_today > vol_ma5) and (vol_today > b_vol_min) and (((close_price - ma60) / ma60 * 100) < b_ma60_bias)

            if a_cond or b_cond:
                # 戰術精算
                buy_zone = f"{ma20:.1f} ~ {ma20 * 1.02:.1f}"
                stop_loss = ma20 * 0.97
                target = close_price * 1.15
                status = "🟢 可佈局" if close_price <= (ma20 * 1.02) else "🟡 觀察等待"
                
                # 隔日沖警示
                warning = "⚠️ 爆量/隔日沖風險" if vol_today > (vol_ma5 * 3) else ""
                
                strategy = []
                if a_cond: strategy.append("A策略")
                if b_cond: strategy.append("B策略")

                results.append({
                    "代號": ticker,
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
            st.error(f"{ticker} 發生錯誤: {e}")
            
        time.sleep(0.5) # 防封鎖延遲
        progress_bar.progress((i + 1) / len(raw_tickers))

    status_text.text("掃描完成！")
    
    # 輸出表格
    if results:
        st.dataframe(pd.DataFrame(results), use_container_width=True)
    else:
        st.info("目前沒有符合條件的標的。")
