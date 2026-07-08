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

# 👑 掛載全新的 V34 中央大腦
try: import war_room_engine
except ImportError: war_room_engine = None

# ==========================================
# 💾 本機記憶與雲端備份系統 (V31 核心防護)
# ==========================================
DATA_FILE = "hios_data.json"
DB_FILE = "broker_memory.db"

def load_local_memory():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'portfolio' not in st.session_state: st.session_state['portfolio'] = data.get('portfolio', [])
                if 'watchlist' not in st.session_state: st.session_state['watchlist'] = data.get('watchlist', [])
        except Exception as e:
            st.sidebar.error(f"記憶讀取失敗: {e}")
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

# ==========================================
# 🛡️ V32 戰略預備隊模組 (資料庫讀取與 UI)
# ==========================================
def load_strategic_benchmarks():
    try:
        conn = sqlite3.connect(DB_FILE)
        query = """
            SELECT stock_id AS '代號', stock_name AS '名稱', rating AS '評級', strategy_type AS '戰略定位', key_brokers AS '關鍵鎖碼分點', entry_bias AS '建檔乖離率(%)'
            FROM strategic_benchmarks
            ORDER BY CASE rating WHEN 'S' THEN 1 WHEN 'A+' THEN 2 WHEN 'A' THEN 3 WHEN 'A-' THEN 4 ELSE 5 END
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception: return pd.DataFrame()

def render_strategic_benchmarks_ui():
    st.header("🛡️ V32 戰略預備隊 (法人級避險金庫)")
    st.markdown("這裡存放了總司令親自篩選的 **S/A級 投信鐵三角與大戶避險名單**。")
    
    if st.button("📥 點我！一鍵將 16 檔菁英寫入金庫", type="primary"):
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS strategic_benchmarks (record_date TEXT, stock_id TEXT, stock_name TEXT, rating TEXT, strategy_type TEXT, key_brokers TEXT, entry_bias REAL, PRIMARY KEY (record_date, stock_id))''')
            insert_sql = '''INSERT INTO strategic_benchmarks (record_date, stock_id, stock_name, rating, strategy_type, key_brokers, entry_bias) VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(record_date, stock_id) DO UPDATE SET rating=excluded.rating, strategy_type=excluded.strategy_type, key_brokers=excluded.key_brokers, entry_bias=excluded.entry_bias'''
            elite_list = [
                ("1722", "台肥", "S", "大戶避險金庫", "摩根大通, 美商高盛", 0.0), ("2820", "華票", "S", "大戶避險金庫", "摩根大通, 摩根士丹利", 0.0),
                ("2617", "台航", "S", "大戶避險金庫", "摩根大通, 凱基台北", 0.0), ("1201", "味全", "A-", "大戶避險金庫", "南部大戶連線, 凱基台北", 0.0),
                ("2855", "統一證", "A+", "投信鐵三角-金融", "投信", 1.87), ("2845", "遠東銀", "A+", "投信鐵三角-金融", "投信", 1.44),
                ("5876", "上海商銀", "A", "投信鐵三角-金融", "投信", 0.35), ("2356", "英業達", "A", "投信鐵三角-AI肉盾", "投信", -1.86),
                ("2377", "微星", "A", "投信鐵三角-AI肉盾", "投信", -0.67), ("2382", "廣達", "A", "投信鐵三角-AI肉盾", "投信", 0.31),
                ("3231", "緯創", "A", "投信鐵三角-AI肉盾", "投信", -1.91), ("2376", "技嘉", "A", "投信鐵三角-AI肉盾", "投信", -3.60),
                ("2610", "華航", "A", "投信鐵三角-運輸", "投信", 0.16), ("2618", "長榮航", "A", "投信鐵三角-運輸", "投信", 1.10),
                ("2633", "台灣高鐵", "A", "投信鐵三角-運輸", "投信", 1.22), ("2646", "星宇航空", "A", "投信鐵三角-運輸", "投信", 1.13)
            ]
            records = [("2026-07-07", *item) for item in elite_list]
            cursor.executemany(insert_sql, records)
            conn.commit()
            conn.close()
            st.success("✅ 報告總司令：16 檔菁英已成功寫入金庫！請按鍵盤『R』重新整理網頁。")
        except Exception as e: st.error(f"寫入失敗: {e}")
    st.divider()

    df_benchmarks = load_strategic_benchmarks()
    if not df_benchmarks.empty:
        st.dataframe(df_benchmarks, use_container_width=True, hide_index=True)
    else:
        st.warning("目前資料庫中尚無戰略預備隊名單，請點擊上方按鈕進行建檔。")

# ==========================================
# ⚙️ 系統全域設定
# ==========================================
st.set_page_config(page_title="HIOS Wave Radar V34", page_icon="🎯", layout="wide", initial_sidebar_state="expanded")
load_local_memory()

def main():
    st.sidebar.title("🎯 HIOS Wave Radar")
    st.sidebar.caption("V34 戰情指揮中心版")
    
    st.sidebar.header("📂 1. 數據引擎")
    uploaded_csvs = st.sidebar.file_uploader("上傳法人買賣超 CSV (建議上傳 3~5 天份量)", type=['csv'], accept_multiple_files=True)
    
    # ==========================================
    # 🔥 V34 戰情指揮中心 (一鍵總掃描)
    # ==========================================
    st.sidebar.header("🔥 2. 戰情指揮中心")
    if uploaded_csvs and len(uploaded_csvs) > 0:
        if st.sidebar.button("🔴 一鍵啟動每日總掃描", type="primary", use_container_width=True):
            if war_room_engine:
                st.title("🔥 V34 總司令終極戰報")
                war_room_engine.run_grand_unification(uploaded_csvs)
                st.stop() # 🛑 停止渲染下方舊版分頁，讓總司令專注於終極戰報！
            else:
                st.sidebar.error("找不到 `war_room_engine.py` 模組！請確認檔案已建立。")
                
    st.sidebar.header("⚙️ 3. 動態濾網設定")
    filter_vol_min = st.sidebar.number_input("💧 5日均量下限 (張)", min_value=0, max_value=20000, value=3000, step=500)
    filter_bias_max = st.sidebar.number_input("🔥 月線乖離率上限 (%)", min_value=1.0, max_value=50.0, value=5.0, step=0.5)
    filter_resonance = st.sidebar.checkbox("🤝 嚴格族群濾網 (共振 >= 3)", value=True)
    
    st.sidebar.header("🗄️ 4. 系統記憶與備份")
    if st.sidebar.button("💾 手動儲存本機記憶", use_container_width=True):
        if save_local_memory(): st.sidebar.success("✅ 記憶已成功寫入本機硬碟！")
        else: st.sidebar.error("❌ 寫入失敗！")
            
    st.sidebar.download_button(label="📥 下載系統備份檔 (ZIP)", data=create_backup_zip(), file_name="Hios_Backup.zip", mime="application/zip", use_container_width=True)
    
    uploaded_zip = st.sidebar.file_uploader("📤 上傳備份檔還原系統", type=['zip'])
    if uploaded_zip is not None:
        if st.sidebar.button("🔄 執行還原", type="primary", use_container_width=True):
            if restore_from_zip(uploaded_zip): st.sidebar.success("✅ 系統還原成功！請重整網頁。")
            else: st.sidebar.error("❌ 還原失敗，請確認 ZIP 格式。")
                
    # ==========================================
    # 🚀 主戰情室 (八大核心面板 - 舊版獨立模組)
    # ==========================================
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "🌐 總體風控", "🚀 雷達掃描", "🛡️ 持股監控", "⏳ 時光膠囊", 
        "🎯 主力 X 光狙擊", "🗄️ 歷史記憶庫", "🛡️ 戰略預備隊", "👑 V33 真龍雷達"
    ])
    
    with tab1:
        if market_filter: market_filter.render_market_dashboard()
        else: st.warning("⚠️ 找不到 `market_filter.py`")
            
    with tab2:
        st.header("🚀 雷達掃描室 (V32 雙引擎系統)")
        radar_mode = st.radio("請選擇雷達掃描作戰模式：", ["🛡️ 投信波段真龍 (抓波段主將)", "🥷 主力潛伏妖股 (抓偷吃貨黑手)"], horizontal=True)
        st.divider()
        if uploaded_csvs and len(uploaded_csvs) > 0:
            if radar_mode == "🛡️ 投信波段真龍 (抓波段主將)":
                if strategy_core: strategy_core.run_radar(uploaded_csvs, filter_bias_max, filter_resonance, filter_vol_min)
                else: st.warning("⚠️ 找不到 `strategy_core.py`")
            elif radar_mode == "🥷 主力潛伏妖股 (抓偷吃貨黑手)":
                if strategy_stealth: strategy_stealth.run_stealth_radar(uploaded_csvs)
                else: st.warning("⚠️ 找不到 `strategy_stealth.py`")
        else:
            st.info("👈 請先從左側邊欄上傳「法人買賣超 CSV (可多選)」以啟動雷達。")
            
    with tab3:
        if portfolio_monitor: portfolio_monitor.render_portfolio_monitor()
        else: st.warning("⚠️ 找不到 `portfolio_monitor.py`")

    with tab4:
        if backtest_engine: backtest_engine.render_time_capsule()
        else: st.warning("⚠️ 找不到 `backtest_engine.py`")
            
    with tab5:
        if yahoo_sniper: yahoo_sniper.render_sniper_module()
        else: st.warning("⚠️ 找不到 `yahoo_sniper.py`")
            
    with tab6:
        if broker_memory: broker_memory.render_memory_dashboard()
        else: st.warning("⚠️ 找不到 `broker_memory.py`")
            
    with tab7:
        render_strategic_benchmarks_ui()
        
    with tab8:
        if strategy_v33_dragon:
            strategy_v33_dragon.render_v33_ui(uploaded_csvs)
        else:
            st.warning("⚠️ 找不到 `strategy_v33_dragon.py`，請確認檔案已建立。")

if __name__ == "__main__":
    main()
