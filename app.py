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

# ==========================================
# 系統初始化與版面設定
# ==========================================
st.set_page_config(page_title="HIOS 波段雷達 V15.1", layout="wide")

st.sidebar.title("🚀 HIOS 系統導覽")
page = st.sidebar.radio("功能模組", [
    "🔍 雷達掃描 (動態記憶版)",
    "📊 策略績效追蹤 (回測)",
    "📈 互動 K 線圖"
])

def get_stock_name(code):
    if code in twstock.codes: return twstock.codes[code].name
    return "未知"

# ==========================================
# 頁面 1：雷達掃描 (V15.1 參數記憶快照)
# ==========================================
if page == "🔍 雷達掃描 (動態記憶版)":
    st.title("🚀 HIOS 波段雷達 (V15.1 參數記憶版)")
    
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

            # === V15.1 升級：儲存策略快照 (包含參數記憶) ===
            st.markdown("---")
            st.subheader("💾 策略快照建檔 (供未來績效追蹤)")
            snapshot_name = st.text_input("為這份名單命名 (例如: 20260616_A策略_投信大買)", f"{datetime.now().strftime('%Y%m%d')}_精選名單")
            if st.button("💾 儲存此名單為歷史快照"):
                snapshot_data = {}
                if os.path.exists("strategy_snapshots.json"):
                    try:
                        with open("strategy_snapshots.json", "r", encoding="utf-8") as f:
                            snapshot_data = json.load(f)
                    except: pass
                
                records = df_display[['代號', '名稱', '收盤價', '符合策略']].to_dict('records')
                
                # 將當下的參數一起打包存檔
                snapshot_data[snapshot_name] = {
                    "date": datetime.now().strftime("%Y-%m-%d"),
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
                st.success(f"✅ 快照 [{snapshot_name}] 已成功儲存！請前往左側「📊 策略績效追蹤」檢視。")
        else:
            st.warning("⚠️ 目前參數下沒有符合條件的股票，請嘗試放寬乖離率或降低投信買超門檻！")

# ==========================================
# 頁面 2：策略績效追蹤 (V15.1 顯示參數版)
# ==========================================
elif page == "📊 策略績效追蹤 (回測)":
    st.title("📊 策略績效追蹤與保鮮期驗證")
    st.markdown("載入歷史快照，系統將自動抓取今日最新價格，瞬間結算策略勝率與報酬率！")
    
    SNAPSHOT_FILE = "strategy_snapshots.json"
    if not os.path.exists(SNAPSHOT_FILE):
        st.warning("⚠️ 目前沒有任何歷史快照。請先到「雷達掃描」頁面，篩選出名單後點擊【儲存此名單為歷史快照】！")
    else:
        with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
            snapshot_data = json.load(f)
        
        if not snapshot_data:
            st.warning("⚠️ 快照庫為空。")
        else:
            col1, col2 = st.columns([3, 1])
            selected_snapshot = col1.selectbox("📂 選擇要追蹤的歷史快照", list(snapshot_data.keys()))
            
            if col2.button("🚀 結算最新績效"):
                data = snapshot_data[selected_snapshot]
                records = data["records"]
                save_date = data["date"]
                params = data.get("parameters", {}) # 讀取當時的參數
                
                st.info(f"📅 快照建立日期：{save_date} | 追蹤檔數：{len(records)} 檔")
                
                # === V15.1 升級：顯示當時的參數配方 ===
                if params:
                    with st.expander("🔍 點擊檢視當時的【篩選參數配方】"):
                        for k, v in params.items():
                            st.markdown(f"- **{k}**: `{v}`")
                
                results = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, rec in enumerate(records):
                    ticker = rec["代號"]
                    name = rec["名稱"]
                    entry_price = rec["收盤價"]
                    strategy = rec["符合策略"]
                    
                    status_text.text(f"正在結算 {ticker} {name} 的最新價格...")
                    
                    yf_ticker = f"{ticker}.TW" if twstock.codes.get(ticker) and twstock.codes[ticker].market == '上市' else f"{ticker}.TWO"
                    try:
                        df_current = yf.download(yf_ticker, period="5d", progress=False)
                        if not df_current.empty:
                            if isinstance(df_current.columns, pd.MultiIndex): 
                                df_current.columns = df_current.columns.get_level_values(0)
                            current_price = float(df_current['Close'].iloc[-1])
                            return_pct = round((current_price - entry_price) / entry_price * 100, 2)
                            
                            results.append({
                                "代號": ticker, "名稱": name, "策略": strategy,
                                "進場價 (快照)": entry_price, "最新價 (今日)": round(current_price, 2),
                                "報酬率 (%)": return_pct,
                                "狀態": "🔴 虧損" if return_pct < 0 else "🟢 獲利"
                            })
                    except: pass
                    time.sleep(0.1)
                    progress_bar.progress((i + 1) / len(records))
                    
                status_text.empty()
                
                if results:
                    df_res = pd.DataFrame(results)
                    avg_return = round(df_res["報酬率 (%)"].mean(), 2)
                    win_rate = round(len(df_res[df_res["報酬率 (%)"] > 0]) / len(df_res) * 100, 2)
                    
                    st.markdown("### 🏆 策略結算報告")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("📈 平均報酬率", f"{avg_return}%", f"{avg_return}%")
                    m2.metric("🎯 策略勝率", f"{win_rate}%")
                    m3.metric("⏳ 經過天數", f"自 {save_date} 至今")
                    
                    st.dataframe(df_res, use_container_width=True)

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
                    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線', increasing_line_color='red', decreasing_line_color='green')])
                    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='月線 (MA20)'))
                    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='blue', width=1.5), name='季線 (MA60)'))
                    fig.update_layout(title=f"{name} ({chart_ticker}) 近半年技術線圖", yaxis_title='股價 (元)', xaxis_rangeslider_visible=False, template='plotly_dark', height=600)
                    st.plotly_chart(fig, use_container_width=True)
                else: st.error("找不到該檔股票的資料。")
            except Exception as e: st.error(f"繪圖發生錯誤: {e}")
