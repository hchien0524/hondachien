import json, os, requests, time
from datetime import datetime
import streamlit as st
import yfinance as yf
import pandas as pd
import twstock
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="HIOS 波段雷達 V16.1", layout="wide")
st.sidebar.title("🚀 HIOS 系統導覽")
page = st.sidebar.radio("功能模組", ["🔍 雷達掃描 (動態記憶版)", "📊 策略競技場 (多維度回測)", "📈 互動 K 線圖"])

def get_stock_name(code):
    return twstock.codes[code].name if code in twstock.codes else "未知"

# ==========================================
# 頁面 1：雷達掃描 (V16.1 動態記憶與快照)
# ==========================================
if page == "🔍 雷達掃描 (動態記憶版)":
    st.title("🚀 HIOS 波段雷達 (V16.1 旗艦版)")
    CACHE_FILE = "market_data_cache.json"

    if 'raw_market_data' not in st.session_state:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    cd = json.load(f)
                    st.session_state['raw_market_data'] = cd.get('data', [])
                    st.session_state['last_update'] = cd.get('time', '未知')
            except:
                st.session_state['raw_market_data'], st.session_state['last_update'] = [], "尚未抓取"
        else:
            st.session_state['raw_market_data'], st.session_state['last_update'] = [], "尚未抓取"

    @st.cache_data
    def get_market_tickers(m_type):
        tm = "上市" if "上市" in m_type else "上櫃"
        return [f"{c}{'.TW' if tm=='上市' else '.TWO'}" for c, i in twstock.codes.items() if i.type=='股票' and i.market==tm and len(c)==4], {c: i.name for c, i in twstock.codes.items() if i.type=='股票' and i.market==tm and len(c)==4}

    st.sidebar.header("📥 第一步：資料獲取設定")
    st.sidebar.info(f"💾 資料庫最後更新：\n**{st.session_state.get('last_update', '尚未抓取')}**")
    scan_mode = st.sidebar.radio("掃描範圍：", ("自選股 (快速)", "上市 (TWSE) 約900檔", "上櫃 (TPEx) 約800檔"))
    tickers_input = st.sidebar.text_area("自選股代號 (逗號分隔)", "2382, 3413, 3015, 8210, 2421") if scan_mode == "自選股 (快速)" else ""
    
    st.sidebar.markdown("---")
    chip_source = st.sidebar.radio("籌碼資料來源：", ("手動上傳 CSV (100%準確)", "自動抓取 (TWSE上市，可能不穩)"))
    uploaded_chip_csv = st.sidebar.file_uploader("上傳今日三大法人 CSV", type=["csv"]) if "手動" in chip_source else None

    if st.sidebar.button("🚀 啟動資料抓取 (每日只需按一次)"):
        chip_data = {}
        if uploaded_chip_csv:
            try:
                df_chip = pd.read_csv(uploaded_chip_csv)
                cc = [c for c in df_chip.columns if '代號' in c or '代碼' in c or 'Code' in c][0]
                fc = [c for c in df_chip.columns if '外資' in c][0]
                ic = [c for c in df_chip.columns if '投信' in c][0]
                for _, r in df_chip.iterrows():
                    c = str(r[cc]).replace('=', '').replace('"', '').strip()
                    chip_data[c] = {"外資": pd.to_numeric(str(r[fc]).replace(',',''), errors='coerce') or 0, "投信": pd.to_numeric(str(r[ic]).replace(',',''), errors='coerce') or 0}
            except: st.sidebar.error("CSV 解析失敗")
        elif "自動" in chip_source:
            try:
                res = requests.get("https://openapi.twse.com.tw/v1/fund/T86_ALL", timeout=10 )
                if res.status_code == 200:
                    for item in res.json():
                        c = str(item.get('Code', '')).strip()
                        chip_data[c] = {"外資": float(str(item.get('ForeignInvestorDifference', '0')).replace(',', ''))/1000, "投信": float(str(item.get('InvestmentTrustDifference', '0')).replace(',', ''))/1000}
            except: pass

        target_tickers, stock_names_dict = [], {}
        if scan_mode == "自選股 (快速)":
            for t in [x.strip() for x in tickers_input.split(",")]:
                pc = t.split('.')[0]
                if pc in twstock.codes:
                    stock_names_dict[pc] = twstock.codes[pc].name
                    target_tickers.append(f"{pc}{'.TW' if twstock.codes[pc].market == '上市' else '.TWO'}")
                else: target_tickers.append(f"{pc}.TW")
        else: target_tickers, stock_names_dict = get_market_tickers(scan_mode)

        raw_results, progress_bar, status_text = [], st.progress(0), st.empty()
        for i, ticker in enumerate(target_tickers):
            pc = ticker.split('.')[0]
            c_name = stock_names_dict.get(pc, "未知")
            status_text.text(f"下載 {ticker} {c_name} ... ({i+1}/{len(target_tickers)})")
            try:
                df = yf.download(ticker, period="6mo", progress=False)
                if len(df) >= 60:
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    df['MA20'], df['MA60'], df['Vol'] = df['Close'].rolling(20).mean(), df['Close'].rolling(60).mean(), df['Volume']/1000
                    df['Vol_MA5'] = df['Vol'].rolling(5).mean()
                    latest = df.iloc[-1]
                    raw_results.append({
                        "代號": pc, "名稱": c_name, "收盤價": round(float(latest['Close']), 1), 
                        "MA20": float(latest['MA20']), "MA60": float(latest['MA60']), 
                        "成交量(張)": int(latest['Vol']), "5日均量": float(latest['Vol_MA5']),
                        "投信買賣超(張)": chip_data.get(pc, {}).get("投信", 0), "外資買賣超(張)": chip_data.get(pc, {}).get("外資", 0)
                    })
            except: pass
            time.sleep(0.05)
            progress_bar.progress((i + 1) / len(target_tickers))

        st.session_state['raw_market_data'] = raw_results
        st.session_state['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump({'time': st.session_state['last_update'], 'data': raw_results}, f, ensure_ascii=False)
        except: pass
        status_text.success(f"✅ 完成！已存入 {len(raw_results)} 檔股票。")

    if st.session_state.get('raw_market_data'):
        st.markdown("### ⚙️ 第二步：動態參數篩選 (瞬間完成)")
        df_raw = pd.DataFrame(st.session_state['raw_market_data'])
        
        # 1. 參數控制區收納與提示
        with st.expander("⚙️ 展開進階參數設定 (點擊展開/收合)", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            a_ma20 = c1.slider("A策略 MA20 乖離上限(%)", 1.0, 15.0, 5.0, help="限制股價不能離月線太遠，控制追高風險。")
            b_ma60 = c2.slider("B策略 MA60 乖離上限(%)", 1.0, 20.0, 10.0, help="限制股價不能離季線太遠。")
            b_vol = c3.slider("B策略 成交量門檻(張)", 500, 10000, 3000, help="過濾掉流動性太差的冷門股。")
            min_it = c4.number_input("投信買超大於(張)", -10000, 10000, 100, 100, help="跟著投信大哥走，尋找籌碼認養股。")

        df_raw['A條件'] = (df_raw['收盤價'] > df_raw['MA20']) & (((df_raw['收盤價'] - df_raw['MA20']) / df_raw['MA20'] * 100) < a_ma20)
        df_raw['B條件'] = (df_raw['成交量(張)'] > df_raw['5日均量']) & (df_raw['成交量(張)'] > b_vol) & (((df_raw['收盤價'] - df_raw['MA60']) / df_raw['MA60'] * 100) < b_ma60)
        df_filtered = df_raw[(df_raw['A條件'] | df_raw['B條件']) & (df_raw['投信買賣超(張)'] >= min_it)].copy()

        if not df_filtered.empty:
            # 4. 狀態標籤徽章化
            def format_strategy(row):
                res = []
                if row['A條件']: res.append("🟢 A策略")
                if row['B條件']: res.append("🔥 B策略")
                return " + ".join(res)
            
            df_filtered['符合策略'] = df_filtered.apply(format_strategy, axis=1)
            df_filtered['MA20乖離(%)'] = round((df_filtered['收盤價'] - df_filtered['MA20']) / df_filtered['MA20'] * 100, 1)
            df_filtered['建議買區'] = df_filtered['MA20'].apply(lambda x: f"{x:.1f} ~ {x * 1.02:.1f}")
            df_filtered['停損價'] = round(df_filtered['MA20'] * 0.97, 1)
            
            df_display = df_filtered[['代號', '名稱', '收盤價', '符合策略', '投信買賣超(張)', '外資買賣超(張)', 'MA20乖離(%)', '成交量(張)', '建議買區', '停損價']].sort_values(by="投信買賣超(張)", ascending=False)
            
            st.markdown("---")
            # 2. 頂部戰情儀表板
            st.markdown("### 📊 今日戰情儀表板")
            m1, m2, m3 = st.columns(3)
            m1.metric("🎯 符合條件總數", f"{len(df_display)} 檔精銳")
            top_stock = df_display.iloc[0]
            m2.metric("🔥 投信買超冠軍", f"{top_stock['名稱']} ({top_stock['代號']})", f"{int(top_stock['投信買賣超(張)'])} 張")
            m3.metric("📈 最高月線乖離", f"{df_display['MA20乖離(%)'].max()}%")
            
            st.markdown("---")
            st.success("🎯 瞬間篩選完畢！請參考下方精美戰報：")
            
            # 3. 數據表格視覺化升級
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "投信買賣超(張)": st.column_config.ProgressColumn(
                        "投信買賣超(張)",
                        help="法人籌碼集中度",
                        format="%d",
                        min_value=0,
                        max_value=int(df_display['投信買賣超(張)'].max()) if df_display['投信買賣超(張)'].max() > 0 else 1000,
                    ),
                    "成交量(張)": st.column_config.NumberColumn("成交量(張)", format="%d"),
                    "外資買賣超(張)": st.column_config.NumberColumn("外資買賣超(張)", format="%d"),
                    "MA20乖離(%)": st.column_config.NumberColumn("MA20乖離(%)", format="%.1f %%"),
                    "收盤價": st.column_config.NumberColumn("收盤價", format="%.1f")
                }
            )

            st.markdown("---")
            st.subheader("💾 策略快照建檔 (供未來績效追蹤)")
            snap_name = st.text_input("為這份名單命名", f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_策略名單")
            if st.button("💾 儲存此名單為歷史快照"):
                snap_data = {}
                if os.path.exists("strategy_snapshots.json"):
                    try:
                        with open("strategy_snapshots.json", "r", encoding="utf-8") as f: snap_data = json.load(f)
                    except: pass
                snap_data[snap_name] = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "parameters": {"A策略 MA20 乖離上限(%)": a_ma20, "B策略 MA60 乖離上限(%)": b_ma60, "B策略 成交量門檻(張)": b_vol, "投信買超大於(張)": min_it},
                    "records": df_display[['代號', '名稱', '收盤價', '符合策略']].to_dict('records')
                }
                with open("strategy_snapshots.json", "w", encoding="utf-8") as f: json.dump(snap_data, f, ensure_ascii=False, indent=4)
                st.success(f"✅ 快照 [{snap_name}] 已成功儲存！")
        else: st.warning("⚠️ 目前參數下沒有符合條件的股票！")
    

# ==========================================
# 頁面 2：策略競技場 (V16.1 永久記憶版)
# ==========================================
elif page == "📊 策略競技場 (多維度回測)":
    st.title("⚔️ 策略競技場 (多維度回測與比對)")
    st.markdown("選擇多個歷史快照進行 A/B 測試。**系統會自動記憶上次的結算結果，無需重複等待！**")
    
    SNAP_FILE, CACHE_FILE = "strategy_snapshots.json", "arena_cache.json"
    if 'arena_cache' not in st.session_state:
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f: st.session_state['arena_cache'] = json.load(f)
        except: st.session_state['arena_cache'] = None

    if not os.path.exists(SNAP_FILE): st.warning("⚠️ 目前沒有任何歷史快照。請先到「雷達掃描」頁面儲存快照！")
    else:
        with open(SNAP_FILE, "r", encoding="utf-8") as f: snap_data = json.load(f)
        if not snap_data: st.warning("⚠️ 快照庫為空。")
        else:
            sel_snaps = st.multiselect("📂 選擇要追蹤與比對的歷史快照 (可多選)", list(snap_data.keys()), default=list(snap_data.keys())[-1:])
            
            if st.button("🚀 強制重新連線結算 (獲取最新股價)"):
                if not sel_snaps: st.warning("請至少選擇一個快照！")
                else:
                    comp_res, all_det = [], {}
                    pb, st_txt = st.progress(0), st.empty()
                    tot = sum([len(snap_data[s]["records"]) for s in sel_snaps])
                    proc = 0
                    
                    for s_name in sel_snaps:
                        data = snap_data[s_name]
                        s_res = []
                        for rec in data["records"]:
                            t, n, ep = rec["代號"], rec["名稱"], rec["收盤價"]
                            st_txt.text(f"結算 [{s_name}] {t} {n} ...")
                            yf_t = f"{t}{'.TW' if twstock.codes.get(t) and twstock.codes[t].market == '上市' else '.TWO'}"
                            try:
                                df_c = yf.download(yf_t, period="5d", progress=False)
                                if not df_c.empty:
                                    if isinstance(df_c.columns, pd.MultiIndex): df_c.columns = df_c.columns.get_level_values(0)
                                    cp = float(df_c['Close'].iloc[-1])
                                    s_res.append({"代號": t, "名稱": n, "進場價": ep, "最新價": round(cp, 2), "報酬率(%)": round((cp-ep)/ep*100, 2)})
                            except: pass
                            proc += 1
                            pb.progress(proc / tot)
                            time.sleep(0.05)
                            
                        if s_res:
                            df_r = pd.DataFrame(s_res)
                            comp_res.append({"快照名稱": s_name, "建立時間": data["date"], "檔數": len(s_res), "平均報酬率(%)": round(df_r["報酬率(%)"].mean(), 2), "勝率(%)": round(len(df_r[df_r["報酬率(%)"]>0])/len(df_r)*100, 2)})
                            all_det[s_name] = {"df": df_r.to_dict('records'), "params": data.get("parameters", {})}
                    
                    st_txt.empty()
                    if comp_res:
                        cd = {"update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "comparison_results": comp_res, "all_details": all_det}
                        try:
                            with open(CACHE_FILE, "w", encoding="utf-8") as f: json.dump(cd, f, ensure_ascii=False, indent=4)
                            st.session_state['arena_cache'] = cd
                            st.success("✅ 結算完成！結果已永久儲存。")
                        except: pass

            if st.session_state.get('arena_cache'):
                cache = st.session_state['arena_cache']
                st.info(f"💾 本地快取資料 (最後結算: **{cache['update_time']}**)。")
                st.markdown("---")
                st.header("🏆 策略競技場總結算")
                df_comp = pd.DataFrame(cache["comparison_results"]).sort_values(by="平均報酬率(%)", ascending=False)
                fig = px.bar(df_comp, x="快照名稱", y="平均報酬率(%)", color="勝率(%)", title="各策略平均報酬率比對", text="平均報酬率(%)", template="plotly_dark", color_continuous_scale="Viridis")
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df_comp, use_container_width=True)
                
                st.markdown("### 📋 各策略詳細配方與明細")
                for s_name in df_comp["快照名稱"]:
                    with st.expander(f"📂 展開檢視：{s_name}"):
                        det = cache["all_details"].get(s_name, {})
                        st.json(det.get("params", {}))
                        st.dataframe(pd.DataFrame(det.get("df", [])), use_container_width=True)

# ==========================================
# 頁面 3：互動 K 線圖
# ==========================================
elif page == "📈 互動 K 線圖":
    st.title("📈 專業互動 K 線圖與均線分析")
    c1, c2 = st.columns([1, 3])
    with c1:
        c_ticker = st.text_input("請輸入股票代號 (例如: 2382)", "3413")
        c_btn = st.button("📊 繪製線圖")
        
    if c_btn and c_ticker:
        with st.spinner("繪製中..."):
            ts = f"{c_ticker}{'.TW' if twstock.codes.get(c_ticker) and twstock.codes[c_ticker].market == '上市' else '.TWO'}"
            try:
                df = yf.download(ts, period="6mo", progress=False)
                if df.empty: df = yf.download(f"{c_ticker}{'.TWO' if ts.endswith('.TW') else '.TW'}", period="6mo", progress=False)
                if not df.empty:
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    df['MA20'], df['MA60'] = df['Close'].rolling(20).mean(), df['Close'].rolling(60).mean()
                    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線')])
                    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='MA20'))
                    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='blue', width=1.5), name='MA60'))
                    fig.update_layout(title=f"{get_stock_name(c_ticker)} ({c_ticker}) 近半年技術線圖", yaxis_title='股價', xaxis_rangeslider_visible=False, template='plotly_dark', height=600)
                    st.plotly_chart(fig, use_container_width=True)
                else: st.error("找不到資料。")
            except Exception as e: st.error(f"錯誤: {e}")

