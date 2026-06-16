
import streamlit as st
import yfinance as yf
import pandas as pd
import time

st.set_page_config(layout="wide", page_title="HIOS 波段雷達")

st.title("HIOS 波段雷達 (Streamlit 核心引擎 - 自訂名單 MVP 版)")

# --- 側邊欄 (Sidebar) 動態參數與 UI 介面 ---
st.sidebar.header("策略參數設定")

# 自選股輸入框
stock_input = st.sidebar.text_area(
    "請輸入掃描名單 (股票代號，以逗號分隔)",
    "2382, 3413, 3015, 8210, 2421, 6274"
)

# 核心參數
ma20_deviation_limit = st.sidebar.slider(
    "A策略 MA20 正乖離上限 (%)",
    min_value=0.0, max_value=10.0, value=5.0, step=0.1
)
ma60_deviation_limit = st.sidebar.slider(
    "B策略 MA60 正乖離上限 (%)",
    min_value=0.0, max_value=20.0, value=10.0, step=0.1
)
volume_threshold = st.sidebar.slider(
    "B策略 成交量門檻 (張)",
    min_value=1000, max_value=10000, value=3000, step=100
)

# 進階籌碼與基本面濾網
st.sidebar.subheader("進階濾網")
filter_institutional_buying = st.sidebar.checkbox(
    "啟用投信鎖碼濾網 (近 5 日買超 >= 3 天)", value=True
)
filter_margin_decrease = st.sidebar.checkbox(
    "啟用融資洗盤濾網 (近 5 日融資減少)", value=True
)
filter_fundamental_yoy = st.sidebar.checkbox(
    "啟用基本面濾網 (最新月營收 YoY > 0)", value=True
)

# --- 核心資料工程 ---
def get_stock_data(ticker_list):
    data = {}
    for ticker in ticker_list:
        if not ticker:
            continue
        full_ticker = f"{ticker}.TW" if ".TW" not in ticker.upper() else ticker.upper()
        st.info(f"正在抓取 {full_ticker} 資料...")
        try:
            # 抓取足夠的歷史資料以計算 MA60 (約 90 天)
            stock = yf.Ticker(full_ticker)
            hist = stock.history(period="90d")

            if not hist.empty:
                # 計算均線
                hist['MA5'] = hist['Close'].rolling(window=5).mean()
                hist['MA20'] = hist['Close'].rolling(window=20).mean()
                hist['MA60'] = hist['Close'].rolling(window=60).mean()

                # 計算成交量均量
                hist['Volume_MA5'] = hist['Volume'].rolling(window=5).mean()

                # 取得最新資料
                latest = hist.iloc[-1]
                prev_5_days = hist.iloc[-5:]

                # 計算正乖離
                ma20_deviation = ((latest['Close'] - latest['MA20']) / latest['MA20']) * 100 if latest['MA20'] else 0
                ma60_deviation = ((latest['Close'] - latest['MA60']) / latest['MA60']) * 100 if latest['MA60'] else 0

                # 籌碼面與基本面模擬 (yfinance 無法直接取得，先模擬)
                # 投信鎖碼濾網 (近 5 日買超 >= 3 天) - 模擬為 True
                institutional_buying_ok = True
                # 融資洗盤濾網 (近 5 日融資減少) - 模擬為 True
                margin_decrease_ok = True
                # 基本面濾網 (最新月營收 YoY > 0) - 模擬為 True
                fundamental_yoy_ok = True

                data[ticker] = {
                    '股票代號': ticker,
                    '收盤價': latest['Close'],
                    'MA20': latest['MA20'],
                    'MA60': latest['MA60'],
                    'MA20正乖離(%)': ma20_deviation,
                    'MA60正乖離(%)': ma60_deviation,
                    '今日成交量(張)': latest['Volume'] / 1000, # 股數轉張數
                    '5日均量(張)': latest['Volume_MA5'] / 1000, # 股數轉張數
                    '投信鎖碼': institutional_buying_ok,
                    '融資洗盤': margin_decrease_ok,
                    '基本面YoY': fundamental_yoy_ok,
                    'Volume_Raw': latest['Volume'] # 儲存原始成交量用於計算
                }
            else:
                st.warning(f"無法取得 {full_ticker} 的歷史資料，已跳過。")
        except Exception as e:
            st.error(f"抓取 {full_ticker} 資料時發生錯誤: {e}，已跳過。")
        time.sleep(0.5) # 防封鎖
    return pd.DataFrame.from_dict(data, orient='index')

# 處理使用者輸入的股票代號
if stock_input:
    raw_tickers = [t.strip() for t in stock_input.split(',') if t.strip()]
    processed_tickers = [f"{t}.TW" if ".TW" not in t.upper() else t.upper() for t in raw_tickers]
    
    stock_df = get_stock_data(processed_tickers)

    if not stock_df.empty:
        # --- 戰術精算與主畫面輸出 ---
        results = []
        for index, row in stock_df.iterrows():
            ticker = row['股票代號']
            close_price = row['收盤價']
            ma20 = row['MA20']
            ma60 = row['MA60']
            ma20_dev = row['MA20正乖離(%)']
            ma60_dev = row['MA60正乖離(%)']
            current_volume = row['今日成交量(張)']
            avg_volume_5d = row['5日均量(張)']
            volume_raw = row['Volume_Raw']

            # A策略條件：收盤價 > MA20 且正乖離 < 設定值。
            strategy_a_ok = (close_price > ma20) and (ma20_dev < ma20_deviation_limit)

            # B策略條件：今日成交量 > 5日均量 且 > 設定值，MA60 正乖離 < 設定值。
            strategy_b_ok = (
                (current_volume > avg_volume_5d) and 
                (current_volume * 1000 > volume_threshold * 1000) and 
                (ma60_dev < ma60_deviation_limit)
            )

            # 進階濾網邏輯 (若勾選則啟用，未勾選則視為通過)
            filter_ok = True
            if filter_institutional_buying and not row['投信鎖碼']:
                filter_ok = False
            if filter_margin_decrease and not row['融資洗盤']:
                filter_ok = False
            if filter_fundamental_yoy and not row['基本面YoY']:
                filter_ok = False

            # 隔日沖警示邏輯
            warning = ""
            if volume_raw > (row['Volume_MA5'] * 3):
                warning = "⚠️ 爆量/隔日沖風險"
            
            # 戰術面板
            suggested_buy_low = ma20
            suggested_buy_high = ma20 * 1.02
            stop_loss_price = ma20 * 0.97
            target_price = close_price * 1.15

            status = ""
            if close_price <= suggested_buy_high:
                status = "🟢 可佈局"
            else:
                status = "🟡 觀察等待"

            results.append({
                '股票代號': ticker,
                '收盤價': f"{close_price:.2f}",
                'MA20': f"{ma20:.2f}",
                'MA60': f"{ma60:.2f}",
                'MA20正乖離(%)': f"{ma20_dev:.2f}",
                'MA60正乖離(%)': f"{ma60_dev:.2f}",
                '今日成交量(張)': f"{current_volume:.0f}",
                '5日均量(張)': f"{avg_volume_5d:.0f}",
                'A策略符合': "✅" if strategy_a_ok else "❌",
                'B策略符合': "✅" if strategy_b_ok else "❌",
                '濾網符合': "✅" if filter_ok else "❌",
                '建議買區': f"{suggested_buy_low:.2f} ~ {suggested_buy_high:.2f}",
                '停損價': f"{stop_loss_price:.2f}",
                '目標價': f"{target_price:.2f}",
                '狀態': status,
                '警示': warning
            })
        
        results_df = pd.DataFrame(results)
        st.dataframe(results_df, hide_index=True)
    else:
        st.warning("請輸入有效的股票代號以進行掃描。")
else:
    st.info("請在左側側邊欄輸入股票代號，然後點擊 Enter 或離開輸入框以開始掃描。")
