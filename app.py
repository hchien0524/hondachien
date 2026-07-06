import streamlit as st
import pandas as pd
import json
from datetime import datetime # 🌟 V31 新增：用來取得今日日期

# ==========================================
# 🛡️ 模組安全掛載區 (維持您原本的完美架構)
# ==========================================
try:
    import strategy_core
except ImportError:
    strategy_core = None

try:
    import backtest_engine
except ImportError:
    backtest_engine = None

try:
    import portfolio_monitor
except ImportError:
    portfolio_monitor = None

try:
    import memory_module
except ImportError:
    memory_module = None

try:
    import market_filter
except ImportError:
    market_filter = None

# --- 🌟 V31 新增模組安全掛載區 ---
try:
    import yahoo_sniper
except ImportError:
    yahoo_sniper = None

try:
    import broker_memory
except ImportError:
    broker_memory = None
# --------------------------------

st.set_page_config(
    page_title="HIOS Wave Radar V31", # 升級為 V31
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.sidebar.title("🎯 HIOS Wave Radar")
    st.sidebar.caption("V31 旗艦視覺版") # 升級為 V31
    
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
    
    # 掛載 Base64 記憶模組
    if memory_module:
        memory_module.render_memory_module()
    else:
        st.sidebar.warning("⚠️ 找不到 `memory_module.py`")

    # ==========================================
    # ⚔️ 旗艦級 UI：戰區 Tabs 重構 (無縫加入 V31)
    # ==========================================
    # 🌟 將原本的 4 個 Tab 擴充為 6 個 Tab
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🌐 總體風控", 
        "🚀 雷達掃描", 
        "🛡️ 持股監控", 
        "⏳ 時光膠囊",
        "🎯 主力狙擊 (V31)", 
        "🧠 歷史記憶 (V31)"
    ])
    
    with tab1:
        if market_filter:
            market_filter.render_market_dashboard()
        else:
            st.warning("⚠️ 找不到 `market_filter.py`")
            
    with tab2:
        st.header("🚀 雷達掃描室 (雙腦評分系統)")
        if uploaded_csvs and len(uploaded_csvs) > 0:
            st.info(f"📂 已成功載入 {len(uploaded_csvs)} 份 CSV 檔案，準備啟動內部迴圈。")
            if strategy_core:
                try:
                    strategy_core.run_radar(uploaded_csvs, filter_bias_max, filter_resonance, filter_vol_min)
                except Exception as e:
                    st.error(f"雷達運算發生錯誤: {e}")
            else:
                st.warning("⚠️ 找不到 `strategy_core.py`")
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

    # ==========================================
    # 🎯 V31 新增戰區：主力 X 光狙擊
    # ==========================================
    with tab5:
        st.header("🎯 V31 主力 X 光狙擊機 (Yahoo 籌碼透視)")
        st.markdown("輸入股票代號，系統將自動潛入 Yahoo 抓取今日主力進出，並**無聲無息地存入本地記憶庫**。")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            target_stock = st.text_input("請輸入股票代號 (例: 5443, 2356):", value="5443", key="sniper_input")
            scan_btn = st.button("🚀 啟動狙擊掃描", type="primary", use_container_width=True)
            
        if scan_btn:
            if target_stock:
                if yahoo_sniper and broker_memory:
                    with st.spinner(f"🕵️‍♂️ 正在潛入 Yahoo 抓取 {target_stock} 今日籌碼..."):
                        sniper = yahoo_sniper.YahooSniper()
                        df_result = sniper.scan_target(target_stock)
                        
                        if df_result is not None and not df_result.empty:
                            st.success(f"✅ 破解成功！已取得 {target_stock} 籌碼明細。")
                            st.dataframe(df_result, use_container_width=True)
                            
                            today_str = datetime.now().strftime("%Y-%m-%d")
                            broker_memory.init_db()
                            broker_memory.save_daily_data(today_str, target_stock, df_result)
                            st.info("💾 戰利品已安全存入本地記憶庫 (broker_memory.db)！")
                        else:
                            st.error("❌ 狙擊失敗！目標失去聯繫或防護過強。")
                else:
                    st.error("⚠️ 系統警告：找不到 `yahoo_sniper.py` 或 `broker_memory.py`，無法執行狙擊任務！")
            else:
                st.warning("⚠️ 總司令，請先輸入股票代號！")

    # ==========================================
    # 🧠 V31 新增戰區：歷史記憶庫
    # ==========================================
    with tab6:
        st.header("🧠 歷史記憶庫 (多日籌碼加總)")
        st.markdown("調閱本地資料庫，自動加總過去 N 天的主力買賣超，讓**隔日沖**與**波段鎖碼主力**無所遁形！")
        
        col_m1, col_m2 = st.columns([1, 3])
        with col_m1:
            query_stock = st.text_input("查詢股票代號:", value="5443", key="query_stock")
            query_days = st.slider("查詢天數 (目前為單日測試):", min_value=1, max_value=20, value=5)
            query_btn = st.button("🔍 調閱歷史記憶", type="primary", use_container_width=True)
            
        if query_btn:
            if broker_memory:
                with st.spinner("正在計算歷史籌碼..."):
                    broker_memory.init_db()
                    df_history = broker_memory.get_multi_day_concentration(query_stock, days=query_days)
                    
                    if df_history is not None and not df_history.empty:
                        st.success(f"🎯 成功調閱 {query_stock} 歷史記憶！以下為區間前 15 大主力：")
                        st.dataframe(df_history, use_container_width=True)
                    else:
                        st.warning(f"⚠️ 記憶庫中目前沒有 {query_stock} 的歷史資料。請先到「主力 X 光狙擊」執行抓取任務！")
            else:
                st.error("⚠️ 系統警告：找不到 `broker_memory.py`，無法調閱記憶庫！")

if __name__ == "__main__":
    main()
