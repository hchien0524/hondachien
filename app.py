import json
import os
from datetime import datetime
import requests
import streamlit as st
import yfinance as yf
import pandas as pd
import time
import twstock
import plotly.graph_objects as go
import plotly.express as px

# ==========================================
# 系統初始化與版面設定
# ==========================================
st.set_page_config(page_title="HIOS 波段雷達 V16.1", layout="wide")

st.sidebar.title("🚀 HIOS 系統導覽")
page = st.sidebar.radio("功能模組", [
    "🔍 雷達掃描 (動態記憶版)",
    "📊 策略競技場 (多維度回測)",
    "📈 互動 K 線圖"
])

def get_stock_name(code):
    if code in twstock.codes: return twstock.codes[code].name
    return "未知"

# ==========================================
# 頁面 1：雷達掃描 (V16.0 防覆蓋快照)
# ==========================================
if page == "🔍 雷達掃描 (動態記憶版)":
    st.title("🚀 HIOS 波段雷達 (V16.1 旗艦版)")
    
    CACHE_FILE = "market_data_cache.json"

    if 'raw_market_data' not in st.session_state:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    st.session_state['raw_market_data'] = cache_data.get('data', [])
                    st.session_state['last_update'] = cache_data.get('time', '未知')
            except:
                st.session_state['raw_market_data'] = []
                st.session_state['last_update'] = "尚未抓取"
        else:
            st.session_state['raw_market_data'] = []
            st.session_state['last_update'] = "尚未抓取"

    @st.cache_data
    def get_market_tickers(market_type):
        tickers, names = [], {}
        target_market = "上市" if "上市" in market_type else "上櫃"
        for code, info in twstock.codes.items():
            if info.type == '股票' and info.market == target_market and len(code) == 4:
                tickers.append(f"{code}{'.TW' if target_market == '上市' else '.TWO'}")
                names[code] = info.name
        return tickers, names

    st.sidebar.header("📥 第一步：資料獲取設定")
    st.sidebar.info(f"💾 目前資料庫最後更新：\n**{st.session_state.get('last_update', '尚未抓取')}**")
    
    scan_mode = st.sidebar.radio("掃描範圍：", ("自選股 (快速)", "上市 (TWSE) 約900檔", "上櫃 (TPEx) 約800檔"))
    tickers_input = st.sidebar.text_area("自選股代號 (逗號分隔)", "2382, 3413, 3015, 8210, 2421") if scan_mode == "自選股 (快速)" else ""
    
    st.sidebar.markdown("---")
    chip_source = st.sidebar.radio("籌碼資料來源：", ("手動上傳 CSV (100%準確，強烈建議)", "自動抓取 (TWSE上市，可能不穩)"))
    uploaded_chip_csv = None
    if chip_source == "手動上傳 CSV (100%準確，強烈建議)":
        uploaded_chip_csv = st.sidebar.file_uploader("上傳今日三大法人 CSV", type=["csv"])

    def parse_uploaded_chips(file):
        chip_dict = {}
        try:
            df_chip = pd.read_csv(file)
            code_col = [c for c in df_chip.columns if '代號' in c or '代碼' in c or 'Code' in c][0]
            fi_col = [c for c in df_chip.columns if '外資' in c][0]
            it_col = [c for c in df_chip.columns if '投信' in c][0]
            for _, row in df_chip.iterrows():
                code = str(row[code_col]).replace('=', '').replace('"', '').strip()
                fi_val = pd.to_numeric(str(row[fi_col]).replace(',', ''), errors='coerce')
                it_val = pd.to_numeric(str(row[it_col]).replace(',', ''), errors='coerce')
                chip_dict[code] = {"外資買賣超": fi_val if pd.notna(fi_val) else 0, "投信買賣超": it_val if pd.notna(it_val) else 0}
        except Exception:
            st.sidebar.error("CSV 解析失敗，請確認欄位格式。")
        return chip_dict

    if st.sidebar.button("🚀 啟動資料抓取 (每日只需按一次)"):
        chip_data = {}
        if chip_source == "手動上傳 CSV (100%準確，強烈建議)" and uploaded_chip_csv is not None:
            chip_data = parse_uploaded_chips(uploaded_chip_csv)
        elif chip_source == "自動抓取 (TWSE上市，可能不穩)":
            try:
                res = requests.get("https://openapi.twse.com.tw/v1/fund/T86_ALL", timeout=10 )
                if res.status_code == 200:
                    for item in res.json():
                        code = str(item.get('Code', '')).strip()
                        fi_diff = float(str(item.get('ForeignInvestorDifference', '0')).replace(',', '')) / 1000
                        it_diff = float(str(item.get('InvestmentTrustDifference', '0')).replace(',', '')) / 1000
                        chip_data[code] = {"外資買賣超": round(fi_diff, 1), "投信買賣超": round(it_diff, 1)}
            except: pass

        target_tickers, stock_names_dict = [], {}
        if scan_mode == "自選股 (快速)":
            for t in [x.strip() for x in tickers_input.split(",")]:
                pure_code = t.split('.')[0] 
                if pure_code in twstock.codes:
                    stock_names_dict[pure_code] = twstock.codes[pure_code].name
                    target_tickers.append(f"{pure_code}{'.TW' if twstock.codes[pure_code].market == '上市' else '.TWO'}")
                else: target_tickers.append(f"{pure_code}.TW")
        else: target_tickers, stock_names_dict = get_market_tickers(scan_mode)

        raw_results, progress_bar, status_text = [], st.progress(0), st.empty()
        for i, ticker in enumerate(target_tickers):
            pure_code = ticker.split('.')[0] 
            current_name = stock_names_dict.get(pure_code, "未知")
            status_text.text(f"正在下載 {ticker} {current_name} 原始數據... ({i+1}/{len(target_tickers)})")
            try:
                df = yf.download(ticker, period="6mo", progress=False)
                if df.empty or len(df) < 60: continue
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                
                df['MA20'], df['MA60'], df['Vol'] = df['Close'].rolling(20).mean(), df['Close'].rolling(60).mean(), df['Volume']/1000
                df['Vol_MA5'] = df['Vol'].rolling(5).mean()
                
                latest = df.iloc[-1]
                c, m20, m60, v, vm5 = float(latest['Close']), float(latest['MA20']), float(latest['MA60']), float(latest['Vol']), float(latest['Vol_MA5'])
                
                it_buy = chip_data.get(pure_code, {}).get("投信買賣超", 0)
                fi_buy = chip_data.get(pure_code, {}).get("外資買賣超", 0)

                raw_results.append({
                    "代號": pure_code, "名稱": current_name, "收盤價": round(c, 1), 
                    "MA20": m20, "MA60": m60, "成交量(張)": int(v), "5日均量": vm5,
                    "投信買賣超(張)": it_buy, "外資買賣超(張)": fi_buy
                })
            except: pass
            time.sleep(0.1)
            progress_bar.progress((i + 1) / len(target_tickers))

        st.session_state['raw_market_data'] = raw_results
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state['last_update'] = current_time
        
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump({'time': current_time, 'data': raw_results}, f, ensure_ascii=False)
        except Exception as e:
            st.sidebar.error(f"存檔失敗: {e}")

        status_text.success(f"✅ 數據下載並存檔完成！已將 {len(raw_results)} 檔股票存入本地資料庫。")

    if st.session_state.get('raw_market_data'):
        st.markdown("### ⚙️ 第二步：動態參數篩選 (瞬間完成，關網頁也不會消失)")
        df_raw = pd.DataFrame(st.session_state['raw_market_data'])
        
        col1, col2, col3, col4 = st.columns(4)
        a_ma20_bias = col1.slider("A策略 MA20 乖離上限(%)", 1.0, 15.0, 5.0)
        b_ma60_bias = col2.slider("B策略 MA60 乖離上限(%)", 1.0, 20.0, 10.0)
        b_vol_min = col3.slider("B策略 成交量門檻(張)", 500, 10000, 3000)
        min_it_buy = col4.number_input("投信買超大於(張)", min_value=-10000, max_value=10000, value=100, step=100)

        df_raw['A條件'] = (df_raw['收盤價'] > df_raw['MA20']) & (((df_raw['收盤價'] - df_raw['MA20']) / df_raw['MA20'] * 100) < a_ma20_bias)
        df_raw['B條件'] = (df_raw['成交量(張)'] > df_raw['5日均量']) & (df_raw['成交量(張)'] > b_vol_min) & (((df_raw['收盤價'] - df_raw['MA60']) / df_raw['MA60'] * 100) < b_ma60_bias)
        
        df_filtered = df_raw[(df_raw['A條件'] | df_raw['B條件']) & (df_raw['投信買賣超(張)'] >= min_it_buy)].copy()

        if not df_filtered.empty:
            df_filtered['符合策略'] = df_filtered.apply(lambda x: "+".join([s for s, cond in zip(["A策略", "B策略"], [x['A條件'], x['B條件']]) if cond]), axis=1)
            df_filtered['MA20乖離(%)'] = round((df_filtered['收盤價'] - df_filtered['MA20']) / df_filtered['MA20'] * 100, 1)
            df_filtered['建議買區'] = df_filtered['MA20'].apply(lambda x: f"{x:.1f} ~ {x * 1.02:.1f}")
            df_filtered['停損價'] = round(df_filtered['MA20'] * 0.97, 1)
            
            df_display = df_filtered[['代號', '名稱', '收盤價', '符合策略', '投信買賣超(張)', '外資買賣超(張)', 'MA20乖離(%)', '成交量(張)', '建議買區', '停損價']]
            df_display = df_display.sort_values(by="投信買賣超(張)", ascending=False)
            
            st.success(f"🎯 瞬間篩選完畢！符合條件共 **{len(df_display)}** 檔精銳。")
            st.dataframe(df_display, use_container_width=True)

            st.markdown("---")
            st.subheader("💾 策略快照建檔 (供未來績效追蹤)")
            default_snap_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_策略名單"
            snapshot_name = st.text_input("為這份名單命名 (系統已自動加入時間戳記防覆蓋)", default_snap_name)
            
            if st.button("💾 儲存此名單為歷史快照"):
                snapshot_data = {}
                if os.path.exists("strategy_snapshots.json"):
                    try:
                        with open("strategy_snapshots.json", "r", encoding="utf-8") as f:
                            snapshot_data = json.load(f)
                    except: pass
                
                records = df_display[['代號', '名稱', '收盤價', '符合策略']].to_dict('records')
                
                snapshot_data[snapshot_name] = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "parameters": {
                        "A策略 MA20 乖離上限(%)": a_ma20_bias,
                        "B策略 MA60 乖離上限(%)": b_ma60_bias,
                        "B策略 成交量門檻(張)": b_vol_min,
                        "投信買超大於(張)": min_it_buy
                    },
                    "records": records
                }
                
                with open("strategy_snapshots.json", "w", encoding="utf-8") as f:
                    json.dump(snapshot_data, f, ensure_ascii=False, indent=4)
                st.success(f"✅ 快照 [{snapshot_name}] 已成功儲存！請前往左側「📊 策略競技場」檢視。")
        else:
            st.warning("⚠️ 目前參數下沒有符合條件的股票，請嘗試放寬乖離率或降低投信買超門檻！")

# ==========================================
# 頁面 2：策略競技場 (V16.1 永久記憶版)
# ==========================================
elif page == "📊 策略競技場 (多維度回測)":
    st.title("⚔️ 策略競技場 (多維度回測與比對)")
    st.markdown("選擇多個歷史快照進行 A/B 測試。**系統會自動記憶上次的結算結果，無需重複等待！**")
    
    SNAPSHOT_FILE = "strategy_snapshots.json"
    ARENA_CACHE_FILE = "arena_cache.json"
    
    # 讀取競技場專屬記憶體
    if 'arena_cache' not in st.session_state:
        if os.path.exists(ARENA_CACHE_FILE):
            try:
                with open(ARENA_CACHE_FILE, "r", encoding="utf-8") as f:
                    st.session_state['arena_cache'] = json.load(f)
            except:
                st.session_state['arena_cache'] = None
        else:
            st.session_state['arena_cache'] = None

    if not os.path.exists(SNAPSHOT_FILE):
        st.warning("⚠️ 目前沒有任何歷史快照。請先到「雷達掃描」頁面儲存快照！")
    else:
        with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
            snapshot_data = json.load(f)
        
        if not snapshot_data:
            st.warning("⚠️ 快照庫為空。")
        else:
            selected_snapshots = st.multiselect("📂 選擇要追蹤與比對的歷史快照 (可多選)", list(snapshot_data.keys()), default=list(snapshot_data.keys())[-1:] if snapshot_data else None)
            
            if st.button("🚀 強制重新連線結算 (獲取最新股價)"):
                if not selected_snapshots:
                    st.warning("請至少選擇一個快照進行結算！")
                else:
                    comparison_results = []
                    all_details = {}
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    total_stocks = sum([len(snapshot_data[snap]["records"]) for snap in selected_snapshots])
                    processed_stocks = 0
                    
                    for snap_name in selected_snapshots:
                        data = snapshot_data[snap_name]
                        records = data["records"]
                        save_date = data["date"]
                        params = data.get("parameters", {})
                        
                        snap_results = []
                        
                        for rec in records:
                            ticker = rec["代號"]
                            name = rec["名稱"]
                            entry_price = rec["收盤價"]
                            
                            status_text.text(f"正在結算 [{snap_name}] 中的 {ticker} {name} ...")
                            
                            yf_ticker = f"{ticker}.TW" if twstock.codes.get(ticker) and twstock.codes[ticker].market == '上市' else f"{ticker}.TWO"
                            try:
                                df_current = yf.download(yf_ticker, period="5d", progress=False)
                                if not df_current.empty:
                                    if isinstance(df_current.columns, pd.MultiIndex): 
                                        df_current.columns = df_current.columns.get_level_values(0)
                                    current_price = float(df_current['Close'].iloc[-1])
                                    return_pct = round((current_price - entry_price) / entry_price * 100, 2)
                                    
                                    snap_results.append({
                                        "代號": ticker, "名稱": name,
                                        "進場價": entry_price, "最新價": round(current_price, 2),
                                        "報酬率(%)": return_pct
                                    })
                            except: pass
                            
                            processed_stocks += 1
                            progress_bar.progress(processed_stocks / total_stocks)
                            time.sleep(0.1)
                            
                        if snap_results:
                            df_res = pd.DataFrame(snap_results)
                            avg_return = round(df_res["報酬率(%)"].mean(), 2)
                            win_rate = round(len(df_res[df_res["報酬率(%)"] > 0]) / len(df_res) * 100, 2)
                            
                            comparison_results.append({
                                "快照名稱": snap_name,
                                "建立時間": save_date,
                                "檔數": len(snap_results),
                                "平均報酬率(%)": avg_return,
                                "勝率(%)": win_rate
                            })
                            all_details[snap_name] = {"df": df_res.to_dict('records'), "params": params}
                            
                    status_text.empty()
                    
                    # === V16.1 升級：將結算結果存入實體硬碟 ===
                    if comparison_results:
                        cache_data = {
                            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "comparison_results": comparison_results,
                            "all_details": all_details
                        }
                        try:
                            with open(ARENA_CACHE_FILE, "w", encoding="utf-8") as f:
                                json.dump(cache_data, f, ensure_ascii=False, indent=4)
                            st.session_state['arena_cache'] = cache_data
                            st.success("✅ 結算完成！結果已永久儲存至本地資料庫。")
                        except Exception as e:
                            st.error(f"存檔失敗: {e}")

            # === V16.1 升級：直接讀取並顯示記憶體中的結果 ===
            if st.session_state.get('arena_cache'):
                cache = st.session_state['arena_cache']
                st.info(f"💾 目前顯示為本地快取資料 (最後結算時間: **{cache['update_time']}**)。若需最新股價，請點擊上方按鈕重新結算。")
                
                st.markdown("---")
                st.header("🏆 策略競技場總結算")
                df_comp = pd.DataFrame(cache["comparison_results"]).sort_values(by="平均報酬率(%)", ascending=False)
                
                fig = px.bar(df_comp, x="快照名稱", y="平均報酬率(%)", color="勝率(%)", 
                             title="各策略平均報酬率比對 (顏色越亮代表勝率越高)",
                             text="平均報酬率(%)", template="plotly_dark", color_continuous_scale="Viridis")
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(df_comp, use_container_width=True)
                
                st.markdown("### 📋 各策略詳細配方與明細")
                for snap_name in df_comp["快照名稱"]:
                    with st.expander(f"📂 展開檢視：{snap_name}"):
                        detail = cache["all_details"].get(snap_name, {})
                        st.markdown("**⚙️ 當時篩選參數：**")
                        st.json(detail.get("params", {}))
                        st.dataframe(pd.DataFrame(detail.get("df", [])), use_container_width=True)

# ==========================================
# 頁面 3：互動 K 線圖
# ==========================================
elif page == "📈 互動 K 線圖":
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
                    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線', increasing_line_
