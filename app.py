import streamlit as st
import pandas as pd
import json
import zipfile
import io
import os
import sqlite3

# ==========================================
# 🛡️ 模組安全掛載區 (動態載入，防崩潰機制)
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
try: import strategy_v33_dragon
except ImportError: strategy_v33_dragon = None
try: import war_room_engine
except ImportError: war_room_engine = None

DATA_FILE = "hios_data.json"
DB_FILE = "broker_memory.db"

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

st.set_page_config(page_title="HIOS Wave Radar V34", page_icon="🎯", layout="wide", initial_sidebar_state="expanded")
load_local_memory()

def main():
    st.sidebar.title("🎯 HIOS Wave Radar")
    st.sidebar.caption("V34 戰情指揮中心版")
    
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
    # 🚀 主戰情室 (完美對齊的 9 大分頁)
    # ==========================================
    tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "🔥 終極戰報", 
        "🌐 總體風控", 
        "🚀 雷達掃描", 
        "🛡️ 持股監控", 
        "⏳ 時光膠囊", 
        "🎯 主力 X 光狙擊", 
        "🗄️ 歷史記憶庫", 
        "🛡️ 戰略預備隊", 
        "👑 V33 真龍雷達"
    ])
    
    with tab0:
        st.header("🔥 V34 總司令終極戰報")
        if 'v34_report' in st.session_state:
            st.success(f"🎯 嚴格篩選完畢！共淬鍊出 {len(st.session_state['v34_report'])} 檔 S/A 級菁英！(已自動寫入資料庫)")
            st.dataframe(st.session_state['v34_report'], use_container_width=True, hide_index=True)
            st.info("💡 **CIO 戰略提示：** 請複製上方您感興趣的股票代號（如 8033），切換到【🎯 主力 X 光狙擊】分頁，立刻查出背後是哪個主力分點在鎖碼！")
        else:
            st.info("👈 請從左側邊欄上傳 CSV，並點擊「🔴 一鍵啟動每日總掃描」來生成今日戰報。")

    with tab1:
        if market_filter: market_filter.render_market_dashboard()
    with tab2:
        st.header("🚀 雷達掃描室 (舊版 V32)")
        st.info("此功能已整合至左側『一鍵總掃描』，保留此頁供單獨測試使用。")
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
    with tab8:
        if strategy_v33_dragon: strategy_v33_dragon.render_v33_ui(uploaded_csvs)

if __name__ == "__main__":
    main()
