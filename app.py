import streamlit as st
import pandas as pd
import json
import zipfile
import io
import os
import sqlite3
import time
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

# ==========================================
# 🛡️ 模組安全掛載區
# ==========================================
try: import strategy_core
except ImportError: strategy_core = None
try: import strategy_stealth
except ImportError: strategy_stealth = None
try: import backtest_engine
except ImportError: backtest_engine = None
try: import portfolio_monitor
except ImportError: portfolio_monitor = None
try: import market_filter
except ImportError: market_filter = None
try: import yahoo_sniper
except ImportError: yahoo_sniper = None
try: import broker_memory
except ImportError: broker_memory = None
try: import war_room_engine
except ImportError: war_room_engine = None

DATA_FILE = "hios_data.json"
DB_FILE = "broker_memory.db"

# ==========================================
# 🧠 核心記憶與備份系統
# ==========================================
def load_local_memory():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'portfolio' not in st.session_state: st.session_state['portfolio'] = data.get('portfolio', [])
                if 'watchlist' not in st.session_state: st.session_state['watchlist'] = data.get('watchlist', [])
        except Exception: pass
    else:
        if 'portfolio' not in st.session_state: st.session_state['portfolio'] = []
        if 'watchlist' not in st.session_state: st.session_state['watchlist'] = []

def save_local_memory():
    data = {'portfolio': st.session_state.get('portfolio', []), 'watchlist': st.session_state.get('watchlist', [])}
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception: return False

def create_backup_zip():
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        if os.path.exists(DATA_FILE): zip_file.write(DATA_FILE)
        if os.path.exists(DB_FILE): zip_file.write(DB_FILE)
    return zip_buffer.getvalue()

def restore_from_zip(uploaded_zip):
    try:
        with zipfile.ZipFile(uploaded_zip, "r") as zip_ref: zip_ref.extractall(".")
        load_local_memory()
        return True
    except Exception: return False

def load_strategic_benchmarks():
    try:
        conn = sqlite3.connect(DB_FILE)
        query = "SELECT stock_id AS '代號', stock_name AS '名稱', rating AS '評級', strategy_type AS '戰略定位', key_brokers AS '關鍵鎖碼分點', entry_bias AS '建檔乖離率(%)' FROM strategic_benchmarks ORDER BY CASE rating WHEN 'S' THEN 1 WHEN 'A+' THEN 2 WHEN 'A' THEN 3 WHEN 'A-' THEN 4 ELSE 5 END"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception: return pd.DataFrame()

def render_strategic_benchmarks_ui():
    st.header("🛡️ V32 戰略預備隊 (法人級避險金庫)")
    df_benchmarks = load_strategic_benchmarks()
    if not df_benchmarks.empty:
        st.dataframe(df_benchmarks, use_container_width=True, hide_index=True)
    else:
        st.warning("目前資料庫中尚無戰略預備隊名單。")

# ==========================================
# 🛸 批量爬蟲引擎 (Yahoo 專用)
# ==========================================
def fetch_and_parse_yahoo(stock_id):
    url = f"https://tw.stock.yahoo.com/quote/{stock_id}/broker-trading"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64 )'}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            lines = [text.strip() for text in soup.stripped_strings]
            
            parsed_data = []
            is_yahoo = any("買超券商" in line or "賣超券商" in line for line in lines)
            if is_yahoo:
                headers_set = {"買超券商", "買進", "賣出", "買超張數", "賣超券商", "賣超張數"}
                filtered = [l for l in lines if l not in headers_set]
                i = 0
                while i < len(filtered) - 3:
                    broker = filtered[i]
                    try:
                        buy = int(filtered[i+1].replace(',', ''))
                        sell = int(filtered[i+2].replace(',', ''))
                        net = int(filtered[i+3].replace(',', ''))
                        parsed_data.append((stock_id, broker, buy, sell, net))
                        i += 4
                    except ValueError:
                        i += 1
            return parsed_data
    except Exception:
        pass
    return []

# ==========================================
# ⚙️ 系統全域設定
# ==========================================
st.set_page_config(page_title="HIOS Wave Radar V34.5", page_icon="🎯", layout="wide", initial_sidebar_state="expanded")
load_local_memory()

def main():
    st.sidebar.title("🎯 HIOS Wave Radar")
    st.sidebar.caption("V34.5 批量狙擊版")
    
    st.sidebar.header("📂 1. 數據引擎")
    uploaded_csvs = st.sidebar.file_uploader("上傳法人買賣超 CSV", type=['csv'], accept_multiple_files=True)
    
    st.sidebar.header("🔥 2. 戰情指揮中心")
    if uploaded_csvs and len(uploaded_csvs) > 0:
        if st.sidebar.button("🔴 一鍵啟動每日總掃描", type="primary", use_container_width=True):
            if war_room_engine:
                with st.spinner("戰情中心高速運算中..."):
                    report_df = war_room_engine.run_grand_unification(uploaded_csvs)
                    if report_df is not None and not report_df.empty:
                        st.session_state['v34_report'] = report_df
                        st.sidebar.success("✅ 戰報生成完畢！請查看右側【🔥 終極戰報】分頁。")
            else:
                st.sidebar.error("找不到 `war_room_engine.py` 模組！")
                
    st.sidebar.header("⚙️ 3. 動態濾網設定")
    filter_vol_min = st.sidebar.number_input("💧 5日均量下限 (張)", min_value=0, max_value=20000, value=3000, step=500)
    filter_bias_max = st.sidebar.number_input("🔥 月線乖離率上限 (%)", min_value=1.0, max_value=50.0, value=5.0, step=0.5)
    
    st.sidebar.header("🗄️ 4. 系統記憶與備份")
    if st.sidebar.button("💾 手動儲存本機記憶", use_container_width=True): save_local_memory()
    st.sidebar.download_button(label="📥 下載系統備份檔 (ZIP)", data=create_backup_zip(), file_name="Hios_Backup.zip", mime="application/zip", use_container_width=True)
                
    # ==========================================
    # 🚀 主戰情室
    # ==========================================
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🔥 終極戰報", "🌐 總體風控", "🛡️ 持股監控", "⏳ 時光膠囊", 
        "🎯 主力 X 光狙擊", "🗄️ 歷史記憶庫", "🛡️ 戰略預備隊"
    ])
    
    with tab1:
        st.header("🔥 V34 總司令終極戰報")
        if 'v34_report' in st.session_state and not st.session_state['v34_report'].empty:
            df_report = st.session_state['v34_report']
            st.success(f"🎯 嚴格篩選完畢！共淬鍊出 {len(df_report)} 檔 S/A 級菁英！")
            st.dataframe(df_report, use_container_width=True, hide_index=True)
            
            st.divider()
            
            # ==========================================
            # 🛸 終極武器：批量 X 光掃描
            # ==========================================
            st.subheader("🛸 終極武器：批量 X 光掃描 (全自動寫入記憶庫)")
            st.markdown("一鍵啟動背景爬蟲，將上方所有真龍標的之「主力分點明細」全數抓取並歸檔。")
            
            if st.button("🛸 啟動批量掃描與歸檔", type="primary"):
                stock_list = df_report['代號'].astype(str).tolist()
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS broker_records (
                            record_date TEXT, stock_id TEXT, broker_name TEXT, 
                            buy_vol INTEGER, sell_vol INTEGER, net_vol INTEGER,
                            PRIMARY KEY (record_date, stock_id, broker_name)
                        )
                    ''')
                    
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    total_stocks = len(stock_list)
                    success_count = 0
                    
                    for i, sid in enumerate(stock_list):
                        status_text.text(f"🔍 正在狙擊 {sid} ({i+1}/{total_stocks})...")
                        
                        # 呼叫爬蟲引擎
                        parsed_data = fetch_and_parse_yahoo(sid)
                        
                        if parsed_data:
                            records = [(today_str, sid, broker, buy, sell, net) for (sid, broker, buy, sell, net) in parsed_data]
                            cursor.executemany('''
                                INSERT INTO broker_records (record_date, stock_id, broker_name, buy_vol, sell_vol, net_vol)
                                VALUES (?, ?, ?, ?, ?, ?)
                                ON CONFLICT(record_date, stock_id, broker_name) 
                                DO UPDATE SET buy_vol=excluded.buy_vol, sell_vol=excluded.sell_vol, net_vol=excluded.net_vol
                            ''', records)
                            conn.commit()
                            success_count += 1
                            
                        # 🛡️ 防禦機制：休眠 1 秒避免被 Yahoo 封鎖 IP
                        time.sleep(1)
                        progress_bar.progress((i + 1) / total_stocks)
                        
                    conn.close()
                    status_text.text(f"✅ 批量掃描完成！共成功歸檔 {success_count} 檔標的之主力數據。")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"批量掃描發生錯誤: {e}")

            st.divider()
            
            # 🎯 單兵狙擊 (保留給想單獨看某一檔的總司令)
            st.subheader("🎯 單兵狙擊：送往 X 光狙擊室")
            col1, col2 = st.columns([3, 1])
            with col1:
                options = df_report['代號'].astype(str) + " - " + df_report['名稱']
                selected_target = st.selectbox("請選擇要單獨狙擊的標的：", options.tolist())
            with col2:
                st.write("") 
                st.write("")
                if st.button("🔫 一鍵上膛 (送至 X 光)", use_container_width=True):
                    target_id = selected_target.split(" - ")[0]
                    st.session_state['target_id'] = target_id 
                    st.success(f"✅ {selected_target} 已上膛！請點擊上方【🎯 主力 X 光狙擊】分頁開槍！")
        else:
            st.info("👈 請從左側邊欄上傳 CSV，並點擊「🔴 一鍵啟動每日總掃描」來生成今日戰報。")

    with tab2:
        if market_filter: market_filter.render_market_dashboard()
    with tab3:
        if portfolio_monitor: portfolio_monitor.render_portfolio_monitor()
    with tab4:
        if backtest_engine: backtest_engine.render_time_capsule()
    with tab5:
        if yahoo_sniper: yahoo_sniper.render_sniper_module()
    with tab6:
        if broker_memory: broker_memory.render_memory_dashboard()
    with tab7:
        render_strategic_benchmarks_ui()

if __name__ == "__main__":
    main()
