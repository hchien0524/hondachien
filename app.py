import json, os, requests, time
from datetime import datetime
import streamlit as st
import yfinance as yf
import pandas as pd
import twstock
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="HIOS 波段雷達 V16.2", layout="wide")
st.sidebar.title("🚀 HIOS 系統導覽")
page = st.sidebar.radio("功能模組", ["🔍 雷達掃描", "📊 策略競技場", "📈 互動 K 線圖"])

def get_name(c): return twstock.codes[c].name if c in twstock.codes else "未知"

if page == "🔍 雷達掃描":
    st.title("🚀 HIOS 波段雷達 (V16.2 雙引擎全市場版)")
    CACHE = "market_data_cache.json"

    if 'raw_data' not in st.session_state:
        try:
            with open(CACHE, 'r', encoding='utf-8') as f:
                cd = json.load(f)
                st.session_state['raw_data'], st.session_state['last_upd'] = cd.get('data', []), cd.get('time', '未知')
        except:
            st.session_state['raw_data'], st.session_state['last_upd'] = [], "尚未抓取"

    @st.cache_data
    def get_tickers(m_type):
        tm = "上市" if "上市" in m_type else "上櫃"
        return [f"{c}{'.TW' if tm=='上市' else '.TWO'}" for c, i in twstock.codes.items() if i.type=='股票' and i.market==tm and len(c)==4], {c: i.name for c, i in twstock.codes.items() if i.type=='股票' and i.market==tm and len(c)==4}

    st.sidebar.header("📥 第一步：資料獲取設定")
    st.sidebar.info(f"💾 最後更新：\n**{st.session_state.get('last_upd', '尚未抓取')}**")
    scan_mode = st.sidebar.radio("掃描範圍：", ("自選股", "上市 (約900檔)", "上櫃 (約800檔)", "全市場 (約1700檔)"))
    tickers_in = st.sidebar.text_area("自選股代號", "2382, 3413, 3015") if scan_mode == "自選股" else ""
    
    st.sidebar.markdown("---")
    chip_src = st.sidebar.radio("籌碼來源：", ("手動上傳 CSV (100%準確)", "自動抓取 (上市+上櫃 API)"))
    up_csv = st.sidebar.file_uploader("上傳今日三大法人 CSV", type=["csv"]) if "手動" in chip_src else None

    if st.sidebar.button("🚀 啟動資料抓取"):
        chip_data = {}
        if up_csv:
            try:
                df_c = pd.read_csv(up_csv)
                cc = [c for c in df_c.columns if '代號' in c or '代碼' in c or 'Code' in c][0]
                fc = [c for c in df_c.columns if '外資' in c][0]
                ic = [c for c in df_c.columns if '投信' in c][0]
                for _, r in df_c.iterrows():
                    c = str(r[cc]).replace('=', '').replace('"', '').strip()
                    chip_data[c] = {"外資": pd.to_numeric(str(r[fc]).replace(',',''), errors='coerce') or 0, "投信": pd.to_numeric(str(r[ic]).replace(',',''), errors='coerce') or 0}
            except: st.sidebar.error("CSV 解析失敗")
        elif "自動" in chip_src:
            try:
                res = requests.get("https://openapi.twse.com.tw/v1/fund/T86_ALL", timeout=10 )
                if res.status_code == 200:
                    for i in res.json(): chip_data[str(i.get('Code', '')).strip()] = {"外資": float(str(i.get('ForeignInvestorDifference', '0')).replace(',', ''))/1000, "投信": float(str(i.get('InvestmentTrustDifference', '0')).replace(',', ''))/1000}
            except: pass
            try:
                r_otc = requests.get("https://www.tpex.org.tw/openapi/v1/t112sb0eb", timeout=10 )
                r_otc_it = requests.get("https://www.tpex.org.tw/openapi/v1/t112sb0ec", timeout=10 )
                if r_otc.status_code == 200:
                    for i in r_otc.json():
                        c = str(i.get('SecuritiesCompanyCode', '')).strip()
                        if c not in chip_data: chip_data[c] = {"外資": 0, "投信": 0}
                        chip_data[c]["外資"] = float(str(i.get('Difference', '0')).replace(',', ''))/1000
                if r_otc_it.status_code == 200:
                    for i in r_otc_it.json():
                        c = str(i.get('SecuritiesCompanyCode', '')).strip()
                        if c not in chip_data: chip_data[c] = {"外資": 0, "投信": 0}
                        chip_data[c]["投信"] = float(str(i.get('Difference', '0')).replace(',', ''))/1000
            except: pass

        t_tickers, n_dict = [], {}
        if scan_mode == "自選股":
            for t in [x.strip() for x in tickers_in.split(",")]:
                pc = t.split('.')[0]
                if pc in twstock.codes
