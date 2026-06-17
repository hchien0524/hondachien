import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import io
import requests

# ==========================================
# 模組一：系統初始化與 UI 框架
# ==========================================
st.set_page_config(page_title="HIOS Wave Radar V19.5", layout="wide")
st.title("🌊 HIOS Wave Radar V19.5 - 暴力提取版")
st.markdown("### 終極量化核心：全市場直連 × 暴力數據提取 × 絕對防護")

# ==========================================
# 模組二：全市場名單獲取
# ==========================================
@st.cache_data(ttl=86400)
def fetch_tw_universe():
    stocks = []
    try:
        res_twse = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", timeout=5 )
        if res_twse.status_code == 200:
            for item in res_twse.json():
                if len(str(item.get('Code', ''))) == 4:
                    stocks.append({'代號': str(item['Code']), '名稱': str(item['Name']), '市場': '上市'})
    except: pass
    
    try:
        res_tpex = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes", timeout=5 )
        if res_tpex.status_code == 200:
            for item in res_tpex.json():
                if len(str(item.get('SecuritiesCompanyCode', ''))) == 4:
                    stocks.append({'代號': str(item['SecuritiesCompanyCode']), '名稱': str(item['CompanyName']), '市場': '上櫃'})
    except: pass
    
    df_universe = pd.DataFrame(stocks)
    if df_universe.empty:
        return pd.DataFrame(columns=['代號', '名稱', '市場'])
    return df_universe.drop_duplicates(subset=['代號'])

# ==========================================
# 模組三：暴力數據提取層 (無視排版，直接抽數據)
# ==========================================
def parse_chip_csv(uploaded_file):
    raw_bytes = uploaded_file.read()
    decoded_text = None
    for enc in ['utf-8-sig', 'utf-8', 'cp950', 'big5']:
        try:
            decoded_text = raw_bytes.decode(enc)
            break
        except UnicodeDecodeError: continue
            
    if not decoded_text:
        decoded_text = raw_bytes.decode('cp950', errors='ignore')
        
    lines = decoded_text.splitlines()
    skip_rows = 0
    for i, line in enumerate(lines):
        if '代號' in line.replace(' ', '').replace('"', ''):
            skip_rows = i
            break
            
    df = pd.read_csv(io.StringIO(decoded_text), skiprows=skip_rows)
    
    # 暴力尋標：找出目標欄位的真實名稱
    trust_col, foreign_col, code_col, name_col, turn_col = None, None, None, None, None
    for c in df.columns:
        c_str = str(c).replace(' ', '').replace('"', '').replace('\n', '')
        if '代號' in c_str and not code_col: code_col = c
        elif '名稱' in c_str and not name_col: name_col = c
        elif '投信' in c_str and '買賣超' in c_str and '金額' not in c_str and not trust_col: trust_col = c
        elif ('外資' in c_str or '外陸資' in c_str) and '買賣超' in c_str and '金額' not in c_str and not foreign_col: foreign_col = c
        elif '周轉率' in c_str and not turn_col: turn_col = c
            
    # 建立乾淨的標準資料表
    df_clean = pd.DataFrame()
    
    if code_col: df_clean['代號'] = df[code_col].astype(str).str.strip()
    else: df_clean['代號'] = ""
    
    if name_col: df_clean['名稱'] = df[name_col].astype(str).str.strip()
    else: df_clean['名稱'] = ""
    
    # 過濾純血普通股
    df_clean = df_clean[df_clean['代號'].str.match(r'^\d{4}$')]
    
    # 數字清洗與單位轉換 (股 -> 張)
    def extract_and_clean(target_col):
        if target_col and target_col in df.columns:
            # 移除逗號並轉為數字
            s = pd.to_numeric(df[target_col].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
            # 只要欄位名稱有「股」，或者數字大於 20000，就強制除以 1000 變為「張」
            if '股' in str(target_col) or s.abs().max() > 20000:
                s = np.round(s / 1000, 0)
            return s.loc[df_clean.index] # 對齊 index
        return pd.Series(0, index=df_clean.index)
        
    df_clean['投信買賣超'] = extract_and_clean(trust_col)
    df_clean['外資買賣超'] = extract_and_clean(foreign_col)
    df_clean['周轉率'] = extract_and_clean(turn_col)
    
    return df_clean

# ==========================================
# 模組四：側邊欄戰略控制台
# ==========================================
st.sidebar.header("⚙️ 戰術參數設定")
market_choice = st.sidebar.radio("🎯 掃描市場範圍", ["上市櫃全部", "僅上市", "僅上櫃"])
strategy = st.sidebar.radio("🧠 選擇策略", ["A策略 (低乖離防守)", "B策略 (季線突破動能)"])

st.sidebar.markdown("---")
is_intraday = st.sidebar.checkbox("⚡ 啟用盤中狙擊模式", value=False, 
                                  help="盤中模式將自動放寬「周轉率」與「溫和放量」濾網，避免盤中資料失真。")

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ 絕對濾網 (Hard Filters)")
min_trust_buy = st.sidebar.number_input("投信買超下限 (張)", value=100, step=50)
max_bias = st.sidebar.number_input("MA20 乖離率上限 (%)", value=5.0, step=0.5)
max_turnover = st.sidebar.number_input("周轉率上限 (%)", value=10.
