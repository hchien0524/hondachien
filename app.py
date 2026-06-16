import streamlit as st
import yfinance as yf
import pandas as pd
import time
import twstock
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="HIOS 波段雷達", layout="wide", page_icon="🚀")

st.sidebar.title("HIOS 旗艦系統 V10.0")
page = st.sidebar.radio("請選擇功能模組：", [
    "🌍 市場環境 (資金流向)", "🔍 雷達掃描 (白箱解析)", "🗂️ 股票池管理 (超級AI)", 
    "🛡️ 持股防護罩 (健檢)", "📊 績效與交易紀錄", "📈 互動 K 線圖 (分析)"
])
st.sidebar.markdown("---")

@st.cache_data
def get_stock_name(pure_code):
    return twstock.codes[pure_code].name if pure_code in twstock.codes else "未知"

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
        macro_data = get_market_data({"S&P 500": "^GSPC", "那斯達克": "^IXIC", "費城半導體": "^SOX", "VIX 恐慌指數": "^VIX", "美債10年殖利率": "^TNX"})
        cols1 = st.columns(5)
        for i, (name, metrics) in enumerate(macro_data.items()):
            with cols1[i]:
                if metrics:
                    inv_color = "inverse" if "VIX" in name or "殖利率" in name else "normal"
                    st.metric(label=name, value=f"{metrics['value']:.2f}", delta=f"{metrics['diff']:.2f} ({metrics['pct']:.2f}%)", delta_color=inv_color)
                else: st.metric(label=name, value="無資料", delta="-")
        
        st.markdown("---")
        st.subheader("🇹🇼 台股資金風向球 (板塊輪動)")
        tw_data = get_market_data({"加權指數 (大盤)": "^TWII", "櫃買指數 (中小型)": "^TWOII", "0050 (大型權值)": "0050.TW", "00881 (5G半導體)": "00881.TW", "00878 (高股息避險)": "00878.TW"})
        cols2 = st.columns(5)
        for i, (name, metrics) in enumerate(tw_data.items()):
            with cols2[i]:
                if metrics: st.metric(label=name, value=f"{metrics['value']:.2f}", delta=f"{metrics['diff']:.2f} ({metrics['pct']:.2f}%)")
                else: st.metric(label=name, value="無資料", delta="-")

# ==========================================
# 頁面 2：雷達掃描 (新增評分明細)
# ==========================================
elif page == "🔍 雷達掃描 (白箱解析)":
    st.title("🚀 HIOS 波段雷達 (白箱解析版)")
    
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
                df['RSI'] = 100 - (100 / (1 + gain / loss))
                
                latest = df.iloc[-1]
                c, m20, m60, v, vm5, rsi = float(latest['Close']), float(latest['MA20']), float(latest['MA60']), float(latest['Vol']), float(latest['Vol_MA5']), float(latest['RSI'])
                
                a_cond = (c > m20) and (((c - m20) / m20 * 100) < a_ma20_bias)
                b_cond = (v > vm5) and (v > b_vol_min) and (((c - m60) / m60 * 100) < b_ma60_bias)
                
                if a_cond or b_cond:
                    # 白箱解析：記錄加分原因
                    score = 30
                    details = []
                    if c > m20: score += 15; details.append("站上月線")
                    if m20 > m60: score += 20; details.append("多頭排列")
                    if v > (vm5 * 2): score += 15; details.append("動能爆發")
                    if 50 <= rsi <= 75: score += 20; details.append("RSI強勢")
                    
                    results.append({
                        "代號": pure_code, "名稱": current_name, "收盤價": round(c, 1), 
                        "綜合評分": f"{score}分 {'🌟' * (score // 20)}",
                        "評分明細": " + ".join(details), # 新增欄位
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
            df_res = pd.DataFrame(results)[["代號", "名稱", "收盤價", "綜合評分", "評分明細", "符合策略", "MA20乖離(%)", "成交量(張)", "建議買區", "停損價", "目標價", "狀態", "警示"]]
            st.dataframe(df_res, use_container_width=True)
            st.download_button("📥 下載 CSV 報表", data=df_res.to_csv(index=False).encode('utf-8-sig'), file_name="hios_radar.csv", mime="text/csv")
        else: st.info("目前沒有符合條件的標的。")

# ==========================================
# 頁面 3：股票池管理 (超級 AI 協作)
# ==========================================
elif page == "🗂️ 股票池管理 (超級AI)":
    st.title("🗂️ 核心股票池管理與超級 AI 協作")
    
    uploaded_pool = st.file_uploader("📤 讀取股票池存檔 (CSV)", type=["csv"])
    if uploaded_pool is not None:
        st.session_state['stock_pool'] = pd.read_csv(uploaded_pool)
        st.success("✅ 股票池存檔讀取成功！")

    if 'stock_pool' not in st.session_state:
        st.session_state['stock_pool'] = pd.DataFrame({
            "代號": ["3413", "3015"], "名稱": ["京鼎", "全漢"], "級別": ["A級核心池", "B級核心池"],
            "追蹤筆記": ["技術面85分(多頭排列+RSI強勢)，準備50萬試單", "股本小，昨日爆量突破季線"]
        })
    
    edited_pool = st.data_editor(
        st.session_state['stock_pool'], num_rows="dynamic", use_container_width=True,
        column_config={"級別": st.column_config.SelectboxColumn("級別", options=["A級核心池", "B級核心池", "觀察池"], required=True),
                       "追蹤筆記": st.column_config.TextColumn("追蹤筆記", width="large")}
    )
    st.session_state['stock_pool'] = edited_pool

    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📥 下載股票池存檔 (CSV)", data=edited_pool.to_csv(index=False).encode('utf-8-sig'), file_name="hios_pool.csv", mime="text/csv")
    with col2:
        if st.button("🤖 產生 Manus 超級分析指令 (一鍵複製)"):
            report = "Manus 指揮官呼叫！請啟動你的「聯網搜尋能力」，幫我針對以下《核心股票池》進行全方位健檢：\n\n"
            for _, row in edited_pool.iterrows():
                c_code = row.get('代號', '')
                c_name = row.get('名稱', '')
                c_level = row.get('級別', '')
                c_note = row.get('追蹤筆記', '')
                report += f"### {c_code} {c_name} [{c_level}]\n- **APP技術面筆記**：{c_note}\n\n"
            
            report += "---\n**【Manus 任務指令】**\n"
            report += "1. **籌碼面**：請聯網查詢上述標的近 3 日的「投信/外資買賣超」與「融資券變化」。\n"
            report += "2. **基本面**：請聯網查詢最新的「營收狀況」或「法說會/產業新聞」。\n"
            report += "3. **戰略指導**：結合 APP 給的技術面筆記與你查到的籌碼面，用專業客觀的角度，給我明日的具體進出場建議，並指出我可能忽略的風險。\n"
            
            st.success("✅ 超級指令已生成！請點擊下方複製圖示貼給 Manus，我會立刻為您聯網找資料！")
            st.code(report, language="markdown")

# ==========================================
# 頁面 4：持股防護罩
# ==========================================
elif page == "🛡️ 持股防護罩 (健檢)":
    st.title("🛡️ 持股防護罩 (出場警示系統)")
    if 'holdings' not in st.session_state:
        st.session_state['holdings'] = pd.DataFrame({"股票代號": ["2382", "3413"], "成本價": [370.0, 320.0]})
    edited_df = st.data_editor(st.session_state['holdings'], num_rows="dynamic", use_container_width=True)

    if st.button("🛡️ 啟動持股健檢"):
        results, alerts, progress_text = [], [], st.empty()
        for _, row in edited_df.iterrows():
            code, cost = str(row.get('股票代號', '')).strip(), float(row.get('成本價', 0))
            if not code: continue
            progress_text.text(f"正在健檢 {code} ...")
            ticker = f"{code}{'.TW' if twstock.codes.get(code) and twstock.codes[code].market == '上市' else '.TWO'}"
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
# 頁面 5：績效與交易紀錄
# ==========================================
elif page == "📊 績效與交易紀錄":
    st.title("📊 交易紀錄與績效儀表板")
    
    uploaded_trades = st.file_uploader("📤 讀取交易紀錄存檔 (CSV)", type=["csv"])
    if uploaded_trades is not None:
        st.session_state['trade_records'] = pd.read_csv(uploaded_trades)
        st.success("✅ 交易紀錄讀取成功！")

    if 'trade_records' not in st.session_state:
        st.session_state['trade_records'] = pd.DataFrame({
            "代號": ["2382", "3231", "2379"], "策略": ["A策略", "A策略", "B策略"],
            "出場日": ["2026/05/10", "2026/05/05", "2026/06/02"],
            "進場價": [285.0, 82.0, 498.0], "出場價": [268.0, 96.0, 545.0], "股數": [1000, 2000, 1000]
        })

    edited_trades = st.data_editor(
        st.session_state['trade_records'], num_rows="dynamic", use_container_width=True,
        column_config={"策略": st.column_config.SelectboxColumn("策略", options=["A策略", "B策略"], required=True)}
    )
    st.session_state['trade_records'] = edited_trades
    st.download_button("📥 下載交易紀錄存檔 (CSV)", data=edited_trades.to_csv(index=False).encode('utf-8-sig'), file_name="hios_trades.csv", mime="text/csv")

    df_trades = edited_trades.copy()
    if not df_trades.empty:
        df_trades['損益金額'] = (df_trades['出場價'] - df_trades['進場價']) * df_trades['股數']
        total_trades, win_trades = len(df_trades), len(df_trades[df_trades['損益金額'] > 0])
        win_rate = (win_trades / total_trades) * 100 if total_trades > 0 else 0
        total_profit = df_trades['損益金額'].sum()

        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        col1.metric("總交易次數", f"{total_trades} 次")
        col2.metric("整體勝率", f"{win_rate:.1f} %")
        col3.metric("累積總損益", f"{total_profit:,.0f} 元", delta="獲利" if total_profit > 0 else "虧損")

        df_trades = df_trades.sort_values(by="出場日")
        df_trades['累積損益'] = df_trades['損益金額'].cumsum()
        fig = px.line(df_trades, x="出場日", y="累積損益", markers=True, title="資金成長曲線", template="plotly_dark")
        fig.update_traces(line_color='#00FF00' if total_profit >= 0 else '#FF0000', line_width=3, marker=dict(size=8))
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 頁面 6：互動 K 線圖
# ==========================================
elif page == "📈 互動 K 線圖 (分析)":
    st.title("📈 專業互動 K 線圖與均線分析")
    col1, col2 = st.columns([1, 3])
    with col1:
        chart_ticker = st.text_input("請輸入股票代號 (例如: 2382)", "3413")
        chart_btn = st.button("📊 繪製線圖")
        
    if chart_btn and chart_ticker:
        with st.spinner("正在繪製圖表..."):
            ticker_symbol = f"{chart_ticker}{'.TW' if twstock.codes.get(chart_ticker) and twstock.codes[chart_ticker].market == '上市' else '.TWO'}"
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
