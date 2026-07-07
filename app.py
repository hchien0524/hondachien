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
try:
    import strategy_core
except ImportError:
    strategy_core = None

try:
    import strategy_stealth
except ImportError:
    strategy_stealth = None

try:
    import backtest_engine
except ImportError:
    backtest_engine = None

try:
    import portfolio_monitor
except ImportError:
    portfolio_monitor = None

try:
    import market_filter
except ImportError:
    market_filter = None

try:
    import yahoo_sniper
except ImportError:
    yahoo_sniper = None

try:
    import broker_memory
except ImportError:
    broker_memory = None

# ==========================================
# 💾 本機記憶與雲端備份系統 (V31 核心防護)
# ==========================================
DATA_FILE = "hios_data.json"
DB_FILE = "broker_memory.db"

def load_local_memory():
    """從本機讀取 JSON 記憶"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'portfolio' not in st.session_state:
                    st.session_state['portfolio'] = data.get('portfolio', [])
                if 'watchlist' not in st.session_state:
                    st.session_state['watchlist'] = data.get('watchlist', [])
        except Exception as e:
            st.sidebar.error(f"記憶讀取失敗: {e}")
    else:
        if 'portfolio' not in st.session_state: st.session_state['portfolio'] = []
        if 'watchlist' not in st.session_state: st.session_state['watchlist'] = []

def save_local_memory():
    """將 Session State 存回本機 JSON"""
    data = {
        'portfolio': st.session_state.get('portfolio', []),
        'watchlist': st.session_state.get('watchlist', [])
    }
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        return False

def create_backup_zip():
    """打包 JSON 與 SQLite 為 ZIP"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        if os.path.exists(DATA_FILE):
            zip_file.write(DATA_FILE)
        if os.path.exists(DB_FILE):
            zip_file.write(DB_FILE)
    return zip_buffer.getvalue()

def restore_from_zip(uploaded_zip):
    """從 ZIP 還原檔案並重新載入記憶"""
    try:
        with zipfile.ZipFile(uploaded_zip, "r") as zip_ref:
            zip_ref.extractall(".")
        load_local_memory()
        return True
    except Exception as e:
        return False

# ==========================================
# 🛡️ V32 戰略預備隊模組 (資料庫讀取與 UI)
# ==========================================
def load_strategic_benchmarks():
    """從 SQLite 資料庫讀取戰略預備隊名單，並依據 S/A 級精準排序"""
    try:
        conn = sqlite3.connect(DB_FILE)
        query = """
            SELECT 
                stock_id AS '代號', 
                stock_name AS '名稱', 
                rating AS '評級', 
                strategy_type AS '戰略定位', 
                key_brokers AS '關鍵鎖碼分點', 
                entry_bias AS '建檔乖離率(%)'
            FROM strategic_benchmarks
            ORDER BY 
                CASE rating 
                    WHEN 'S' THEN 1 
                    WHEN 'A+' THEN 2 
                    WHEN 'A' THEN 3 
                    WHEN 'A-' THEN 4 
                    ELSE 5 
                END
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame()

def render_strategic_benchmarks_ui():
    """渲染 🛡️ 戰略預備隊 面板 UI"""
    st.header("🛡️ V32 戰略預備隊 (法人級避險金庫)")
    st.markdown("這裡存放了總司令親自篩選的 **S/A級 投信鐵三角與大戶避險名單**。當大盤崩跌或主將陣亡時，請優先從此金庫挑選換股標的。")
    
    df_benchmarks = load_strategic_benchmarks()
    
    if not df_benchmarks.empty:
        st.dataframe(
            df_benchmarks, 
            use_container_width=True,
            hide_index=True
        )
        st.info("💡 **CIO 戰略提示：** 盤中請密切注意這些標的的『關鍵鎖碼分點』是否出現異常賣超。若 S 級標的遭到倒貨，代表大盤將進入無差別下殺，請立刻提高現金水位！")
    else:
        st.warning("目前資料庫中尚無戰略預備隊名單，請先執行建檔腳本 (seed_benchmarks.py)。")

# ==========================================
# ⚙️ 系統全域設定
# ==========================================
st.set_page_config(
    page_title="HIOS Wave Radar V32",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 啟動時自動載入記憶
load_local_memory()

def main():
    st.sidebar.title("🎯 HIOS Wave Radar")
    st.sidebar.caption("V32 雙引擎波段與潛伏版")
    
    # --- 左側邊欄：資料上傳與濾網 ---
    st.sidebar.header("📂 1. 數據引擎")
    uploaded_csvs = st.sidebar.file_uploader(
        "上傳法人買賣超 CSV (支援多檔歷史資料)", 
        type=['csv'], 
        accept_multiple_files=True
    )
    
    st.sidebar.header("⚙️ 2. 動態濾網設定")
    filter_vol_min = st.sidebar.number_input("💧 5日均量下限 (張)", min_value=0, max_value=20000, value=3000, step=500)
    filter_bias_max = st.sidebar.number_input("🔥 月線乖離率上限 (%)", min_value=1.0, max_value=50.0, value=5.0, step=0.5)
    filter_resonance = st.sidebar.checkbox("🤝 嚴格族群濾網 (共振 >= 3)", value=True)
    
    # --- 左側邊欄：記憶體備份模組 ---
    st.sidebar.header("🗄️ 3. 系統記憶與備份")
    if st.sidebar.button("💾 手動儲存本機記憶", use_container_width=True):
        if save_local_memory():
            st.sidebar.success("✅ 記憶已成功寫入本機硬碟！")
        else:
            st.sidebar.error("❌ 寫入失敗！")
            
    st.sidebar.download_button(
        label="📥 下載系統備份檔 (ZIP)",
        data=create_backup_zip(),
        file_name="Hios_Backup.zip",
        mime="application/zip",
        use_container_width=True
    )
    
    uploaded_zip = st.sidebar.file_uploader("📤 上傳備份檔還原系統", type=['zip'])
    if uploaded_zip is not None:
        if st.sidebar.button("🔄 執行還原", type="primary", use_container_width=True):
            if restore_from_zip(uploaded_zip):
                st.sidebar.success("✅ 系統還原成功！請重整網頁。")
            else:
                st.sidebar.error("❌ 還原失敗，請確認 ZIP 格式。")
                
    # ==========================================
    # 🚀 主戰情室 (七大核心面板)
    # ==========================================
    # CIO 註記：這裡成功加入了第七個 Tab！
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🌐 總體風控", 
        "🚀 雷達掃描", 
        "🛡️ 持股監控", 
        "⏳ 時光膠囊", 
        "🎯 主力 X 光狙擊", 
        "🗄️ 歷史記憶庫",
        "🛡️ 戰略預備隊"  # <--- 新增的 Tab 7
    ])
    
    with tab1:
        if market_filter:
            market_filter.render_market_dashboard()
        else:
            st.warning("⚠️ 找不到 `market_filter.py`")
            
    with tab2:
        st.header("🚀 雷達掃描室 (雙引擎系統)")
        
        radar_mode = st.radio(
            "請選擇雷達掃描作戰模式：", 
            ["🛡️ 投信波段真龍 (抓波段主將)", "🥷 主力潛伏妖股 (抓偷吃貨黑手)"], 
            horizontal=True
        )
        st.divider()
        
        if uploaded_csvs and len(uploaded_csvs) > 0:
            st.info(f"📂 已成功載入 {len(uploaded_csvs)} 份 CSV 檔案，準備啟動內部迴圈。")
            
            if radar_mode == "🛡️ 投信波段真龍 (抓波段主將)":
                if strategy_core:
                    try:
                        strategy_core.run_radar(uploaded_csvs, filter_bias_max, filter_resonance, filter_vol_min)
                    except Exception as e:
                        st.error(f"投信雷達運算發生錯誤: {e}")
                else:
                    st.warning("⚠️ 找不到 `strategy_core.py`")
                    
            elif radar_mode == "🥷 主力潛伏妖股 (抓偷吃貨黑手)":
                if strategy_stealth:
                    try:
                        strategy_stealth.run_stealth_radar(uploaded_csvs)
                    except Exception as e:
                        st.error(f"潛伏雷達運算發生錯誤: {e}")
                else:
                    st.warning("⚠️ 找不到 `strategy_stealth.py`")
        else:
            st.info("👈 請先從左側邊欄上傳「法人買賣超 CSV (可多選)」以啟動雷達。")
            
    with tab3:
        if portfolio_monitor:
            portfolio_monitor.render_portfolio_monitor()
        else:
            st.warning("⚠️ 找不到 `portfolio_monitor.py`")

    with tab4:
        if backtest_engine:
            backtest_engine.render_time_capsule()
        else:
            st.warning("⚠️ 找不到 `backtest_engine.py`")
            
    with tab5:
        if yahoo_sniper:
            yahoo_sniper.render_sniper_module()
        else:
            st.warning("⚠️ 找不到 `yahoo_sniper.py`")
            
    with tab6:
        if broker_memory:
            broker_memory.render_memory_dashboard()
        else:
            st.warning("⚠️ 找不到 `broker_memory.py`")
            
    # CIO 註記：這裡呼叫了 Tab 7 的專屬 UI 函數！
    with tab7:
        render_strategic_benchmarks_ui()

if __name__ == "__main__":
    main()
