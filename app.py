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
        c1, c2, c3, c4 = st.columns(4)
        a_ma20 = c1.slider("A策略 MA20 乖離上限(%)", 1.0, 15.0, 5.0)
        b_ma60 = c2.slider("B策略 MA60 乖離上限(%)", 1.0, 20.0, 10.0)
        b_vol = c3.slider("B策略 成交量門檻(張)", 500, 10000, 3000)
        min_it = c4.number_input("投信買超大於(張)", -10000, 10000, 100, 100)

        df_raw['A條件'] = (df_raw['收盤價'] > df_raw['MA20']) & (((df_raw['收盤價'] - df_raw['MA20']) / df_raw['MA20'] * 100) < a_ma20)
        df_raw['B條件'] = (df_raw['成交量(張)'] > df_raw['5日均量']) & (df_raw['成交量(張)'] > b_vol) & (((df_raw['收盤價'] - df_raw['MA60']) / df_raw['MA60'] * 100) < b_ma60)
        df_filtered = df_raw[(df_raw['A條件'] | df_raw['B條件']) & (
