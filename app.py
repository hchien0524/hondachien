import streamlit as st
import pandas as pd
import json

# 模組安全掛載區
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

st.set_page_config(
    page_title="HIOS Wave Radar V30",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.sidebar.title("🎯 HIOS Wave Radar")
    st.sidebar.caption("V30 旗艦視覺版")
    
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
    # ⚔️ 旗艦級 UI：四大戰區 Tabs 重構
    # ==========================================
    tab1, tab2, tab3, tab4 = st.tabs(["🌐 總體風控", "🚀 雷達掃描", "🛡️ 持股監控", "⏳ 時光膠囊"])
    
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

if __name__ == "__main__":
    main()
