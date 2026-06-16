import streamlit as st
import yfinance as yf
import pandas as pd
import time
import twstock

st.set_page_config(page_title="HIOS 波段雷達", layout="wide", page_icon="🚀")

# --- 側邊欄導覽列 (多頁面切換) ---
st.sidebar.title("HIOS 系統導覽")
page = st.sidebar.radio("請選擇功能模組：", ["🌍 市場環境 (首頁)", "🔍 雷達掃描 (選股)", "🛡️ 持股防護罩 (健檢)"])
st.sidebar.markdown("---")

# --- 共用函數：獲取台股名稱 ---
@st.cache_data
def get_stock_name(pure_code):
    if pure_code in twstock.codes:
        return twstock.codes[pure_code].name
    return "未知"

# ==========================================
# 頁面 1：市場環境 (總經儀表板)
# ==========================================
if page == "🌍 市場環境 (首頁)":
    st.title("🌍 全球市場環境與資金風向")
    st.markdown("在啟動台股雷達前，請先確認全球總經天氣是否適合出航。")
    
    @st.cache_data(ttl=1800)
    def get_macro_data():
        symbols = {
            "S&P 500 (美股指標)": "^GSPC", 
            "那斯達克 (科技股)": "^IXIC", 
            "費城半導體 (台股風向)": "^SOX", 
            "VIX 恐慌指數 (風險)": "^VIX", 
            "美債10年殖利率 (資金)": "^TNX"
        }
        data = {}
        for name, sym in symbols.items():
            try:
                hist = yf.Ticker(sym).history(period="5d")
                if len(hist) >= 2:
                    curr = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[-2]
                    diff = curr - prev
                    pct = (diff / prev) * 100
                    data[name] = {"value": curr, "diff": diff, "pct": pct}
            except:
                data[name] = None
        return data

    with st.spinner("正在載入全球總經數據..."):
        macro_data = get_macro_data()
        cols = st.columns(5)
        for i, (name, metrics) in enumerate(macro_data.items()):
            with cols[i]:
                if metrics:
                    inv_color = "inverse" if "VIX" in name or "殖利率" in name else "normal"
                    st.metric(
                        label=name, 
                        value=f"{metrics['value']:.2f}", 
                        delta=f"{metrics['diff']:.2f} ({metrics['pct']:.2f}%)",
                        delta_color=inv_color
                    )
                else:
                    st.metric(label=name, value="無資料", delta="-")
                    
    st.markdown("---")
    st.subheader("💡 幕僚戰略提示")
    st.info("若 VIX > 20 或 美債殖利率急升，建議減少資金水位；若費半大漲，可積極佈局突破型標的。")

# ==========================================
# 頁面 2：雷達掃描 (核心引擎)
# ==========================================
elif page == "🔍 雷達掃描 (選股)":
    st.title("🚀 HIOS 波段雷達 (全市場掃描)")

    @st.cache_data
    def get_market_data(market_type):
        tickers = []
        names = {}
        target_market = "上市" if market_type == "上市 (TWSE) 約900檔" else "上櫃"
        for code, info in twstock.codes.items():
            if info.type == '股票' and info.market == target_market:
                if len(code) == 4:
                    suffix = ".TW" if target_market == "上市" else ".TWO"
                    tickers.append(f"{code}{suffix}")
                    names[code] = info.name
        return tickers, names

    st.sidebar.header("⚙️ 掃描範圍與參數")
    scan_mode = st.sidebar.radio("請選擇掃描範圍：", ("自選股 (快速)", "上市 (TWSE) 約900檔", "上櫃 (TPEx) 約800檔"))

    tickers_input = ""
    if scan_mode == "自選股 (快速)":
        tickers_input = st.sidebar.text_area("請輸入自選股代號 (逗號分隔)", "2382, 3413, 3015, 8210, 2421, 6274")
    else:
        st.sidebar.info(f"⚠️ 警告：全市場掃描約需 7-10 分鐘，請保持網頁開啟勿關閉。")

    a_ma20_bias = st.sidebar.slider("A策略 MA20 正乖離上限 (%)", 1.0, 15.0, 5.0)
    b_ma60_bias = st.sidebar.slider("B策略 MA60 正乖離上限 (%)", 1.0, 20.0, 10.0)
    b_vol_min = st.sidebar.slider("B策略 成交量門檻 (張)", 500, 10000, 3000)

    if st.button("🚀 啟動掃描"):
        target_tickers = []
        stock_names_dict = {}

        if scan_mode == "自選股 (快速)":
            raw_tickers = [t.strip() for t in tickers_input.split(",")]
            for t in raw_tickers:
                pure_code = t.replace('.TW', '').replace('.TWO', '')
                if pure_code in twstock.codes:
                    stock_names_dict[pure_code] = twstock.codes[pure_code].name
                    market = twstock.codes[pure_code].market
                    suffix = ".TW" if market == "上市" else ".TWO"
                    target_tickers.append(f"{pure_code}{suffix}")
                else:
                    target_tickers.append(f"{pure_code}.TW")
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
                if df.empty or len(df) < 60: continue
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

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

                if pd.isna(ma20) or pd.isna(ma60): continue

                a_cond = (close_price > ma20) and (((close_price - ma20) / ma20 * 100) < a_ma20_bias)
                b_cond = (vol_today > vol_ma5) and (vol_today > b_vol_min) and (((close_price - ma60) / ma60 * 100) < b_ma60_bias)

                if a_cond or b_cond:
                    results.append({
                        "代號": pure_code, "名稱": current_name, "收盤價": round(close_price, 1),
                        "符合策略": "+".join([s for s, c in zip(["A策略", "B策略"], [a_cond, b_cond]) if c]),
                        "MA20乖離(%)": round((close_price - ma20) / ma20 * 100, 1),
                        "成交量(張)": int(vol_today),
                        "建議買區": f"{ma20:.1f} ~ {ma20 * 1.02:.1f}",
                        "停損價": round(ma20 * 0.97, 1),
                        "目標價": round(close_price * 1.15, 1),
                        "狀態": "🟢 可佈局" if close_price <= (ma20 * 1.02) else "🟡 觀察等待",
                        "警示": "⚠️ 爆量/隔日沖風險" if vol_today > (vol_ma5 * 3) else ""
                    })
            except: pass 
            time.sleep(0.2) 
            progress_bar.progress((i + 1) / total_stocks)

        status_text.text(f"掃描完成！共找出 {len(results)} 檔符合條件的標的。")
        if results: st.dataframe(pd.DataFrame(results), use_container_width=True)
        else: st.info("目前沒有符合條件的標的。")

# ==========================================
# 頁面 3：持股防護罩 (健檢)
# ==========================================
elif page == "🛡️ 持股防護罩 (健檢)":
    st.title("🛡️ 持股防護罩 (出場警示系統)")
    st.markdown("請在下方表格輸入您的目前持股與成本價。**資料僅暫存於您的瀏覽器，關閉網頁即銷毀，100% 保障資安。**")

    # 初始化預設持股名單 (可讓使用者自由增刪)
    if 'holdings' not in st.session_state:
        st.session_state['holdings'] = pd.DataFrame({
            "股票代號": ["2382", "3413"],
            "成本價": [370.0, 320.0]
        })

    # 互動式表格 (Data Editor)
    st.info("💡 提示：您可以點擊表格直接修改代號與成本，或點擊最下方空白列新增持股。")
    edited_df = st.data_editor(st.session_state['holdings'], num_rows="dynamic", use_container_width=True)

    if st.button("🛡️ 啟動持股健檢"):
        results = []
        alerts = []
        
        progress_text = st.empty()
        
        for index, row in edited_df.iterrows():
            code = str(row['股票代號']).strip()
            cost = float(row['成本價'])
            
            if not code: continue
            
            progress_text.text(f"正在健檢 {code} ...")
            
            # 判斷上市櫃並抓取資料
            market = twstock.codes.get(code, None)
            suffix = ".TW" if market and market.market == "上市" else ".TWO"
            ticker = f"{code}{suffix}"
            
            try:
                df = yf.download(ticker, period="1mo", progress=False)
                if df.empty:
                    suffix = ".TWO" if suffix == ".TW" else ".TW"
                    df = yf.download(f"{code}{suffix}", period="1mo", progress=False)
                
                if df.empty: continue
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                
                df['MA20'] = df['Close'].rolling(window=20).mean()
                latest = df.iloc[-1]
                close_price = float(latest['Close'])
                ma20 = float(latest['MA20'])
                
                # 計算損益
                roi = ((close_price - cost) / cost) * 100
                name = get_stock_name(code)
                
                # 判定狀態與警示
                status = "🟡 安全續抱"
                action = "持股健康，守穩月線"
                
                if close_price < ma20:
                    status = "🔴 破線警示"
                    action = "已跌破月線，建議減碼或停損！"
                    alerts.append(f"⚠️ **{name} ({code})** 跌破月線 ({ma20:.1f})，目前報價 {close_price:.1f}，請注意風險！")
                elif roi <= -3.0:
                    status = "🔴 停損警示"
                    action = "虧損達 3%，觸發紀律停損！"
                    alerts.append(f"⚠️ **{name} ({code})** 虧損已達 {roi:.1f}%，請嚴格執行停損！")
                elif roi >= 15.0:
                    status = "🟢 停利提示"
                    action = "獲利達標，可分批停利"
                    alerts.append(f"🎉 **{name} ({code})** 獲利已達 {roi:.1f}%，建議將部分獲利放口袋！")

                results.append({
                    "代號": code,
                    "名稱": name,
                    "成本價": cost,
                    "最新收盤價": round(close_price, 1),
                    "月線(MA20)": round(ma20, 1),
                    "目前報酬率(%)": round(roi, 1),
                    "狀態": status,
                    "系統建議": action
                })
                
            except Exception as e:
                pass
                
        progress_text.empty()
        
        # 顯示警示大框框
        if alerts:
            st.error("### 🚨 系統偵測到出場訊號！")
            for alert in alerts:
                st.markdown(alert)
        else:
            st.success("### ✅ 目前所有持股皆安全，未觸發任何出場訊號！")
            
        # 顯示詳細健檢報表
        st.markdown("### 📊 持股健檢詳細報表")
        if results:
            st.dataframe(pd.DataFrame(results), use_container_width=True)
