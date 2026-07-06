import streamlit as st
import pandas as pd
import json
import time
import random
from datetime import datetime

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
    page_title="HIOS Wave Radar V31",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.sidebar.title("🎯 HIOS Wave Radar")
    st.sidebar.caption("V31 旗艦視覺版")
    
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
    
    if memory_module:
        memory_module.render_memory_module()
    else:
        st.sidebar.warning("⚠️ 找不到 `memory_module.py`")

    # ==========================================
    # ⚔️ 旗艦級 UI：戰區 Tabs 重構
    # ==========================================
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
    # 🎯 V31 雙模式狙擊槍 (全頻段訊號攔截版)
    # ==========================================
    with tab5:
        st.header("🎯 V31 主力 X 光狙擊機 (Yahoo 籌碼透視)")
        
        # --- 模式 1：單發精準狙擊 ---
        st.subheader("🔫 模式一：單發精準狙擊")
        col1, col2 = st.columns([1, 3])
        with col1:
            target_stock = st.text_input("請輸入股票代號 (例: 5443):", value="5443", key="sniper_input")
            scan_btn = st.button("🚀 啟動單發狙擊", type="primary", use_container_width=True)
            
        if scan_btn and target_stock:
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
                        st.info("💾 戰利品已安全存入本地記憶庫！")
                    else:
                        st.error("❌ 狙擊失敗！目標失去聯繫或防護過強。")
            else:
                st.error("⚠️ 系統警告：找不到 `yahoo_sniper.py` 或 `broker_memory.py`！")

        st.markdown("---")
        
        # --- 模式 2：雷達連發狙擊 ---
        st.subheader("⚡ 模式二：雷達榜單全收錄 (機槍連發)")
        
        # 🌟 全頻段訊號攔截器：掃描整個 session_state 尋找雷達名單
        intercepted_results = None
        for key, val in st.session_state.items():
            # 檢查是否為 List 且裡面包含字典，且字典有 '代號'
            if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict) and '代號' in val[0]:
                intercepted_results = val
                break
            # 檢查是否為 DataFrame 且包含 '代號'
            elif isinstance(val, pd.DataFrame) and '代號' in val.columns:
                intercepted_results = val.to_dict('records')
                break

        if intercepted_results:
            # 嘗試依照總分排序，如果沒有總分欄位就維持原排序
            try:
                sorted_results = sorted(intercepted_results, key=lambda x: x.get('🔥 總分', 0), reverse=True)
            except:
                sorted_results = intercepted_results
                
            top_10 = sorted_results[:10]
            top_10_codes = [str(r['代號']) for r in top_10]
            
            st.success(f"📡 訊號攔截成功！已從系統底層抓取到 {len(intercepted_results)} 檔真龍名單。")
            
            st.markdown("**🎯 即將執行自動狙擊的目標 (前 10 名主將)：**")
            cols = st.columns(5)
            for i, r in enumerate(top_10):
                stock_name = r.get('名稱', '未知名稱')
                cols[i % 5].info(f"**{r['代號']}**\n\n{stock_name}")
            
            st.write("")
            if st.button(f"🔥 一鍵自動狙擊這 {len(top_10_codes)} 檔主將，並存入記憶庫", type="primary", use_container_width=True):
                if yahoo_sniper and broker_memory:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    sniper = yahoo_sniper.YahooSniper()
                    broker_memory.init_db()
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    
                    success_count = 0
                    for i, code in enumerate(top_10_codes):
                        stock_name = next((r.get('名稱', '') for r in top_10 if str(r['代號']) == code), '')
                        status_text.text(f"🕵️‍♂️ 正在狙擊第 {i+1}/{len(top_10_codes)} 檔：{code} {stock_name} ...")
                        
                        df_result = sniper.scan_target(code)
                        
                        if df_result is not None and not df_result.empty:
                            broker_memory.save_daily_data(today_str, code, df_result)
                            success_count += 1
                            
                        progress_bar.progress((i + 1) / len(top_10_codes))
                        time.sleep(random.uniform(1.0, 3.0)) 
                        
                    status_text.empty()
                    st.success(f"✅ 狙擊任務大獲全勝！成功將 {success_count} 檔真龍的籌碼存入記憶庫。請至「Tab 6 歷史記憶」調閱！")
                else:
                    st.error("⚠️ 系統警告：找不到 `yahoo_sniper.py` 或 `broker_memory.py`！")
        else:
            st.warning("⚠️ 尚未接收到雷達名單。")
            st.info("💡 請先到「Tab 2 🚀 雷達掃描」執行掃描。如果已經掃描過，請點擊下方按鈕強制同步：")
            if st.button("🔄 強制同步雷達資料", use_container_width=True):
                st.rerun()
            
            # 🛠️ 軍師除錯面板：讓總司令看清底層真相
            with st.expander("🛠️ 系統底層記憶體狀態 (軍師除錯用)"):
                st.write("目前記憶體中所有的變數名稱：")
                st.write(list(st.session_state.keys()))

    with tab6:
        st.header("🧠 歷史記憶庫 (多日籌碼加總)")
        st.markdown("調閱本地資料庫，自動加總過去 N 天的主力買賣超，讓**隔日沖**與**波段鎖碼主力**無所遁形！")
        
        col_m1, col_m2 = st.columns([1, 3])
        with col_m1:
            query_stock = st.text_input("查詢股票代號:", value="5443", key="query_stock")
            query_days = st.slider("查詢天數:", min_value=1, max_value=20, value=5)
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
                        st.warning(f"⚠️ 記憶庫中目前沒有 {query_stock} 的歷史資料。請先執行狙擊任務！")
            else:
                st.error("⚠️ 系統警告：找不到 `broker_memory.py`，無法調閱記憶庫！")

if __name__ == "__main__":
    main()
