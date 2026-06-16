import streamlit as st
import yfinance as yf
import pandas as pd
import time
import twstock
import plotly.graph_objects as go

st.set_page_config(page_title="HIOS 波段雷達", layout="wide", page_icon="🚀")

st.sidebar.title("HIOS 旗艦系統 V7.2")
page = st.sidebar.radio("請選擇功能模組：", ["🌍 市場環境 (資金流向)", "🔍 雷達掃描 (綜合評分)", "🛡️ 持股防護罩 (健檢)", "📈 互動 K 線圖 (分析)"])
st.sidebar.markdown("---")

@st.cache_data
def get_stock_name(pure_code):
    if pure_code in twstock.codes: return twstock.codes[pure_code].name
    return "未知"

# ==========================================
# 頁面 1：市場環境
# ==========================================
if page == "🌍 市場環境 (資金流向)":
    st.title("🌍 全球總經與台股資金流向")
    @st.cache_data(ttl=1800)
    def get_market_data(symbols_dict):
        data = {}
        for name, sym in symbols_dict.items():
            try:
                hist = yf.Ticker(sym).history(period="5d")
                if len(hist) >= 2:
                    curr, prev = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
                    data[name] = {"value": curr, "diff": curr - prev, "pct": ((curr - prev) / prev) * 100}
            except: data[name] = None
        return data

    with st.spinner("正在載入市場數據..."):
        st.subheader("🇺🇸 全球總經天氣")
        macro_symbols = {"S&P 500": "^GSPC", "那斯達克": "^IXIC", "費城半導體": "^SOX", "VIX 恐慌指數": "^VIX", "美債10年殖利率": "^TNX"}
        macro_data = get_market_data(macro_symbols)
        cols1 = st.columns(5)
        for i, (name, metrics) in enumerate(macro_data.items()):
            with cols1[i]:
                if metrics:
                    inv_color = "inverse" if "VIX" in name or "殖利率" in name else "normal"
                    st.metric(label=name, value=f"{metrics['value']:.2f}", delta=f"{metrics['diff']:.2f} ({metrics['pct']:.2f}%)", delta_color=inv_color)
                else: st.metric(label=name, value="無資料", delta="-")
        
        st.markdown("---")
        st.subheader("🇹🇼 台股資金風向球 (板塊輪動)")
        tw_symbols = {"加權指數 (大盤)": "^TWII", "櫃買指數 (中小型)": "^TWOII", "0050 (大型權值)": "0050.TW", "00881 (5G半導體)": "00881.TW", "00878 (高股息避險)": "00878.TW"}
        tw_data = get_market_data(tw_symbols)
        cols2 = st.columns(5)
        for i, (name, metrics) in enumerate(tw_data.items()):
            with cols2[i]:
                if metrics: st.metric(label=name, value=f"{metrics['value']:.2f}", delta=f"{metrics['diff']:.2f} ({metrics['pct']:.2f}%)")
                else: st.metric(label=name, value="無資料", delta="-")

# ==========================================
# 頁面 2：雷達掃描
# ==========================================
elif page == "🔍 雷達掃描 (綜合評分)":
    st.title("🚀 HIOS 波段雷達 (全維度評分版)")
    
    @st.cache_data
    def get_market_tickers(market_type):
        tickers, names = [], {}
        target_market = "上市" if "上市" in market_type else "上櫃"
        for code, info in twstock.codes.items():
            if info.type == '股票' and info.market == target_market and len(code) == 4:
                tickers.append(f"{code}{'.TW' if target_market == '上市' else '.TWO'}")
                names[code] = info.name
        return tickers, names

    st.sidebar.header("⚙️ 掃描參數")
    scan_mode = st.sidebar.radio("掃描範圍：", ("自選股 (快速)", "上市 (TWSE) 約900檔", "上櫃 (TPEx) 約800檔"))
    tickers_input = st.sidebar.text_area("自選股代號 (逗號分隔)", "2382, 3413, 3015, 8210, 2421, 6274") if scan_mode == "自選股 (快速)" else ""
    a_ma20_bias = st.sidebar.slider("A策略 MA20 正乖離上限 (%)", 1.0, 15.0, 5.0)
    b_ma60_bias = st.sidebar.slider("B策略 MA60 正乖離上限 (%)", 1.0, 20.0, 10.0)
    b_vol_min = st.sidebar.slider("B策略 成交量門檻 (張)", 500, 10000, 3000)

    if st.button("🚀 啟動掃描"):
        target_tickers, stock_names_dict = [], {}
        if scan_mode == "自選股 (快速)":
            for t in [x.strip() for x in tickers_input.split(",")]:
                pure_code = t.split('.')[0] 
                if pure_code in twstock.codes:
                    stock_names_dict[pure_code] = twstock.codes[pure_code].name
                    target_tickers.append(f"{pure_code}{'.TW' if twstock.codes[pure_code].market == '上市' else '.TWO'}")
                else: target_tickers.append(f"{pure_code}.TW")
        else: target_tickers, stock_names_dict = get_market_tickers(scan_mode)

        results, progress_bar, status_text = [], st.progress(0), st.empty()
        for i, ticker in enumerate(target_tickers):
            pure_code = ticker.split('.')[0] 
            current_name = stock_names_dict.get(pure_code, "未知")
            status_text.text(f"正在掃描 {ticker} {current_name} ... ({i+1}/{len(target_tickers)})")
            try:
                df = yf.download(ticker, period="6mo", progress=False)
                if df.empty or len(df) < 60: continue
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                
                df['MA20'], df['MA60'], df['Vol'] = df['Close'].rolling(20).mean(), df['Close'].rolling(60).mean(), df['Volume']/1000
                df['Vol_MA5'] = df['Vol'].rolling(5).mean()
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df['RSI'] = 100 - (100 / (1 + rs))
                
                latest = df.iloc[-1]
                c, m20, m60, v, vm5, rsi = float(latest['Close']), float(latest['MA20']), float(latest['MA60']), float(latest['Vol']), float(latest['Vol_MA5']), float(latest['RSI'])
                
                a_cond = (c > m20) and (((c - m20) / m20 * 100) < a_ma20_bias)
                b_cond = (v > vm5) and (v > b_vol_min) and (((c - m60) / m60 * 100) < b_ma60_bias)
                
                if a_cond or b_cond:
                    score = 30
                    if c > m20: score += 15
                    if m20 > m60: score += 20
                    if v > (vm5 * 2): score += 15
                    if 50 <= rsi <= 75: score += 20
                    stars = "🌟" * (score // 20)
                    
                    results.append({
                        "代號": pure_code, "名稱": current_name, "收盤價": round(c, 1), "綜合評分": f"{score}分 {stars}",
                        "符合策略": "+".join([s for s, cond in zip(["A策略", "B策略"], [a_cond, b_cond]) if cond]),
                        "MA20乖離(%)": round((c - m20) / m20 * 100, 1), "成交量(張)": int(v),
                        "建議買區": f"{m20:.1f} ~ {m20 * 1.02:.1f}", "停損價": round(m20 * 0.97, 1), "目標價": round(c * 1.15, 1),
                        "狀態": "🟢 可佈局" if c <= (m20 * 1.02) else "🟡 觀察等待", "警示": "⚠️ 爆量風險" if v > (vm5 * 3) else ""
                    })
            except: pass
            time.sleep(0.2)
            progress_bar.progress((i + 1) / len(target_tickers))

        status_text.text(f"掃描完成！共找出 {len(results)} 檔標的。")
        if results:
            columns_order = ["代號", "名稱", "收盤價", "綜合評分", "符合策略", "MA20乖離(%)", "成交量(張)", "建議買區", "停損價", "目標價", "狀態", "警示"]
            df_res = pd.DataFrame(results)[columns_order]
            st.dataframe(df_res, use_container_width=True)
            
            # 完美修復：強制轉成 bytes 並壓上 utf-8-sig 的 BOM 標記
            csv_bytes = df_res.to_csv(index=False).encode('utf-8-sig')
            st.download_button(label="📥 下載 CSV 報表 (支援 Excel 中文)", data=csv_bytes, file_name="hios_radar_report.csv", mime="text/csv")
        else: st.info("目前沒有符合條件的標的。")

# ==========================================
# 頁面 3：持股防護罩
# ==========================================
elif page == "🛡️ 持股防護罩 (健檢)":
    st.title("🛡️ 持股防護罩 (出場警示系統)")
    if 'holdings' not in st.session_state:
        st.session_state['holdings'] = pd.DataFrame({"股票代號": ["2382", "3413"], "成本價": [370.0, 320.0]})
    edited_df = st.data_editor(st.session_state['holdings'], num_rows="dynamic", use_container_width=True)

    if st.button("🛡️ 啟動持股健檢"):
        results, alerts, progress_text = [], [], st.empty()
        for _, row in edited_df.iterrows():
            code, cost = str(row['股票代號']).strip(), float(row['成本價'])
            if not code: continue
            progress_text.text(f"正在健檢 {code} ...")
            market = twstock.codes.get(code, None)
            ticker = f"{code}{'.TW' if market and market.market == '上市' else '.TWO'}"
            try:
                df = yf.download(ticker, period="1mo", progress=False)
                if df.empty: df = yf.download(f"{code}{'.TWO' if ticker.endswith('.TW') else '.TW'}", period="1mo", progress=False)
                if df.empty: continue
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                df['MA20'] = df['Close'].rolling(20).mean()
                c, m20 = float(df.iloc[-1]['Close']), float(df.iloc[-1]['MA20'])
                roi, name = ((c - cost) / cost) * 100, get_stock_name(code)
                
                status, action = "🟡 安全續抱", "持股健康，守穩月線"
                if c < m20: status, action = "🔴 破線警示", "已跌破月線，建議減碼！"; alerts.append(f"⚠️ **{name}** 跌破月線 ({m20:.1f})！")
                elif roi <= -3.0: status, action = "🔴 停損警示", "虧損達 3%，觸發停損！"; alerts.append(f"⚠️ **{name}** 虧損達 {roi:.1f}%！")
                elif roi >= 15.0: status, action = "🟢 停利提示", "獲利達標，可分批停利"; alerts.append(f"🎉 **{name}** 獲利達 {roi:.1f}%！")

                results.append({"代號": code, "名稱": name, "成本價": cost, "最新收盤價": round(c, 1), "月線": round(m20, 1), "報酬率(%)": round(roi, 1), "狀態": status, "建議": action})
            except: pass
        progress_text.empty()
        if alerts:
            st.error("### 🚨 系統偵測到出場訊號！")
            for a in alerts: st.markdown(a)
        else: st.success("### ✅ 目前所有持股皆安全！")
        if results: st.dataframe(pd.DataFrame(results), use_container_width=True)

# ==========================================
# 頁面 4：互動 K 線圖
# ==========================================
elif page == "📈 互動 K 線圖 (分析)":
    st.title("📈 專業互動 K 線圖與均線分析")
    col1, col2 = st.columns([1, 3])
    with col1:
        chart_ticker = st.text_input("請輸入股票代號 (例如: 2382)", "3413")
        chart_btn = st.button("📊 繪製線圖")
        
    if chart_btn and chart_ticker:
        with st.spinner("正在繪製圖表..."):
            market = twstock.codes.get(chart_ticker, None)
            ticker_symbol = f"{chart_ticker}{'.TW' if market and market.market == '上市' else '.TWO'}"
            name = get_stock_name(chart_ticker)
            try:
                df = yf.download(ticker_symbol, period="6mo", progress=False)
                if df.empty: df = yf.download(f"{chart_ticker}{'.TWO' if ticker_symbol.endswith('.TW') else '.TW'}", period="6mo", progress=False)
                if not df.empty:
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    df['MA20'], df['MA60'] = df['Close'].rolling(20).mean(), df['Close'].rolling(60).mean()
                    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線', increasing_line_color='red', decreasing_line_color='green')])
                    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='月線 (MA20)'))
                    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='blue', width=1.5), name='季線 (MA60)'))
                    fig.update_layout(title=f"{name} ({chart_ticker}) 近半年技術線圖", yaxis_title='股價 (元)', xaxis_rangeslider_visible=False, template='plotly_dark', height=600)
                    st.plotly_chart(fig, use_container_width=True)
                else: st.error("找不到該檔股票的資料。")
            except Exception as e: st.error(f"繪圖發生錯誤: {e}")
