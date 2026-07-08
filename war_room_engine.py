import streamlit as st
import pandas as pd
import yfinance as yf
import io
import time
import sqlite3
import requests
from datetime import datetime

# 🎭 偽裝瀏覽器
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

# ==========================================
# 🛡️ 1. 統一資料清洗管線 (Data Pipeline)
# ==========================================
def clean_numeric(val):
    if pd.isna(val): return 0.0
    if isinstance(val, str): val = val.replace(',', '').strip()
    try: return float(val)
    except: return 0.0

def process_raw_csvs(uploaded_csvs):
    """將多份 CSV 洗成一份純淨的股票清單"""
    df_list = []
    for file in uploaded_csvs:
        file.seek(0)
        raw_data = file.read()
        try: decoded = raw_data.decode('utf-8')
        except: decoded = raw_data.decode('cp950', errors='ignore')
        
        lines = decoded.splitlines()
        header_idx = next((i for i, line in enumerate(lines) if '代號' in line or '代碼' in line), 0)
        
        df_temp = pd.read_csv(io.StringIO(decoded), skiprows=header_idx)
        df_temp.columns = df_temp.columns.str.strip().str.replace('"', '')
        
        id_col = next((col for col in df_temp.columns if '代號' in col or '代碼' in col), None)
        name_col = next((col for col in df_temp.columns if '名稱' in col), None)
        buy_col = next((col for col in df_temp.columns if '三大法人買賣超股數' in col or '買賣超' in col), None)
        
        if id_col and name_col and buy_col:
            df_clean = df_temp[[id_col, name_col, buy_col]].copy()
            df_clean.columns = ['代號', '名稱', '買賣超']
            df_clean['代號'] = df_clean['代號'].astype(str).str.replace(r'\D', '', regex=True)
            # 剔除權證與 ETF
            df_clean = df_clean[df_clean['代號'].str.len() == 4]
            df_clean['買賣超'] = df_clean['買賣超'].apply(clean_numeric) / 1000
            df_list.append(df_clean)
            
    if not df_list: return pd.DataFrame()
    
    df_all = pd.concat(df_list, ignore_index=True)
    df_agg = df_all.groupby('代號').agg({'名稱': 'first', '買賣超': 'sum'}).reset_index()
    return df_agg[df_agg['買賣超'] > 0]

# ==========================================
# 🌐 2. 統一聯網快取中心 (API Gateway)
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_market_data(ticker):
    """抓取 K 線，並加入快取與降速防護"""
    try:
        time.sleep(0.3) # 降速防封鎖
        hist = yf.Ticker(f"{ticker}.TW", session=session).history(period="5d")
        if hist.empty: hist = yf.Ticker(f"{ticker}.TWO", session=session).history(period="5d")
        if not hist.empty and len(hist) >= 2:
            return {
                '代號': ticker,
                '今日收盤': hist['Close'].iloc[-1],
                '今日成交量': hist['Volume'].iloc[-1] / 1000,
                '5日總量': hist['Volume'].sum() / 1000,
                '漲跌幅(%)': round((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2] * 100, 2)
            }
    except: pass
    return None

# ==========================================
# 💾 3. 自動寫入歷史金庫 (Auto-Archiving)
# ==========================================
def save_to_history_db(df_report):
    """將今日戰報自動存入 SQLite"""
    try:
        conn = sqlite3.connect('broker_memory.db')
        today_str = datetime.now().strftime("%Y-%m-%d")
        df_report['日期'] = today_str
        df_report.to_sql('daily_war_reports', conn, if_exists='append', index=False)
        conn.close()
        return True
    except Exception as e:
        st.error(f"資料庫寫入失敗: {e}")
        return False

# ==========================================
# 🚀 4. 戰情大融合主程式 (The Pipeline)
# ==========================================
def run_grand_unification(uploaded_csvs):
    st.info("⚙️ 中央大腦啟動：正在清洗資料並過濾雜訊...")
    df_clean = process_raw_csvs(uploaded_csvs)
    if df_clean.empty:
        st.error("❌ 資料清洗失敗，請確認 CSV 格式。")
        return
        
    st.info(f"✅ 成功萃取 {len(df_clean)} 檔純淨個股。正在啟動聯網快取中心...")
    
    # 這裡未來可以把 df_clean 派發給 V32 和 V33 模組
    # 為了展示大一統，我們先做一個基礎的融合戰報
    
    report_data = []
    my_bar = st.progress(0, text="🌐 正在獲取市場動能與籌碼數據...")
    
    for i, row in df_clean.iterrows():
        my_bar.progress((i + 1) / len(df_clean), text=f"🌐 掃描進度: {i+1}/{len(df_clean)}")
        market_data = fetch_market_data(row['代號'])
        
        if market_data and market_data['5日總量'] > 0:
            concentration = (row['買賣超'] / market_data['5日總量']) * 100
            
            # 簡單的 V33 雛形判定 (可擴充)
            rating = "🛡️ 觀察"
            if concentration > 10 and market_data['漲跌幅(%)'] > 0: rating = "👑 S級真龍"
            elif concentration > 5: rating = "🦅 A級潛龍"
            
            if concentration > 2: # 只顯示有一定集中度的標的
                report_data.append({
                    '戰略評級': rating,
                    '代號': row['代號'],
                    '名稱': row['名稱'],
                    '波段買超(張)': int(row['買賣超']),
                    '籌碼集中度(%)': round(concentration, 2),
                    '今日收盤': round(market_data['今日收盤'], 2),
                    '漲跌幅(%)': market_data['漲跌幅(%)']
                })
                
    my_bar.empty()
    df_report = pd.DataFrame(report_data)
    
    if not df_report.empty:
        df_report = df_report.sort_values(by='籌碼集中度(%)', ascending=False).reset_index(drop=True)
        st.success("🎯 三合一終極戰報生成完畢！")
        st.dataframe(df_report, use_container_width=True)
        
        # 自動存檔
        if save_to_history_db(df_report):
            st.toast("💾 戰報已自動備份至歷史記憶庫！")
    else:
        st.warning("⚠️ 今日無符合條件之標的。")
