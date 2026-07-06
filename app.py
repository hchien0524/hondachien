import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ==========================================
# 🛡️ 系統模組載入區
# ==========================================
# 載入 V31 新武器
try:
    import yahoo_sniper
    import broker_memory
except ImportError:
    st.error("⚠️ 系統警告：找不到 yahoo_sniper.py 或 broker_memory.py，請確認檔案是否在同一資料夾！")

# 載入 V30 原有模組 (若您原本有匯入其他模組，請保留在這裡)
# import data_engine
# import strategy_core
# import memory_module

# ==========================================
# 🖥️ 戰情室 UI 初始化
# ==========================================
st.set_page_config(page_title="HIOS Wave Radar V31", page_icon="🌊", layout="wide")

st.title("🌊 HIOS Wave Radar V31 - 終極量化指揮中心")
st.markdown("---")

# 建立四大戰術分頁
tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 主力 X 光狙擊 (V31)", 
    "🧠 歷史記憶庫 (V31)",
    "📡 盤後雷達海選 (V30)", 
    "🛡️ 持股監控中心"
])

# ==========================================
# 🎯 分頁 1：主力 X 光狙擊 (V31 新增)
# ==========================================
with tab1:
    st.subheader("🎯 V31 主力 X 光狙擊機 (Yahoo 籌碼透視)")
    st.markdown("輸入股票代號，系統將自動潛入 Yahoo 抓取今日主力進出，並**無聲無息地存入本地記憶庫**。")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        target_stock = st.text_input("請輸入股票代號 (例: 5443, 2356):", value="5443", key="sniper_input")
        scan_btn = st.button("🚀 啟動狙擊掃描", type="primary", use_container_width=True)
        
    if scan_btn:
        if target_stock:
            with st.spinner(f"🕵️‍♂️ 正在潛入 Yahoo 抓取 {target_stock} 今日籌碼..."):
                # 1. 呼叫狙擊手
                sniper = yahoo_sniper.YahooSniper()
                df_result = sniper.scan_target(target_stock)
                
                if df_result is not None and not df_result.empty:
                    st.success(f"✅ 破解成功！已取得 {target_stock} 籌碼明細。")
                    
                    # 2. 顯示戰報
                    st.dataframe(df_result, use_container_width=True)
                    
                    # 3. 存入本地記憶庫
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    broker_memory.init_db()
                    broker_memory.save_daily_data(today_str, target_stock, df_result)
                    st.info("💾 戰利品已安全存入本地記憶庫 (broker_memory.db)！")
                else:
                    st.error("❌ 狙擊失敗！目標失去聯繫或防護過強。")
        else:
            st.warning("⚠️ 總司令，請先輸入股票代號！")

# ==========================================
# 🧠 分頁 2：歷史記憶庫 (V31 新增)
# ==========================================
with tab2:
    st.subheader("🧠 歷史記憶庫 (多日籌碼加總)")
    st.markdown("調閱本地資料庫，自動加總過去 N 天的主力買賣超，讓**隔日沖**與**波段鎖碼主力**無所遁形！")
    
    col_m1, col_m2 = st.columns([1, 3])
    with col_m1:
        query_stock = st.text_input("查詢股票代號:", value="5443", key="query_stock")
        query_days = st.slider("查詢天數 (目前為單日測試):", min_value=1, max_value=20, value=5)
        query_btn = st.button("🔍 調閱歷史記憶", type="primary", use_container_width=True)
        
    if query_btn:
        with st.spinner("正在計算歷史籌碼..."):
            broker_memory.init_db()
            df_history = broker_memory.get_multi_day_concentration(query_stock, days=query_days)
            
            if df_history is not None and not df_history.empty:
                st.success(f"🎯 成功調閱 {query_stock} 歷史記憶！以下為區間前 15 大主力：")
                st.dataframe(df_history, use_container_width=True)
            else:
                st.warning(f"⚠️ 記憶庫中目前沒有 {query_stock} 的歷史資料。請先到「主力 X 光狙擊」執行抓取任務！")

# ==========================================
# 📡 分頁 3：盤後雷達海選 (V30 原有功能)
# ==========================================
with tab3:
    st.subheader("📡 盤後雷達海選 (三大法人 CSV 掃描)")
    st.info("💡 總司令，請將您原本 V30.6 的 `st.file_uploader` (上傳 CSV) 與海選邏輯程式碼貼在這個區塊下方。")
    # TODO: 貼上您原本的 CSV 處理程式碼

# ==========================================
# 🛡️ 分頁 4：持股監控中心 (V30 原有功能)
# ==========================================
with tab4:
    st.subheader("🛡️ 持股監控中心")
    st.markdown("目前戰情室監控主將：**英業達 (2356)**、**均豪 (5443)**")
    st.info("💡 總司令，請將您原本呼叫 `memory_module.py` 的持股監控程式碼貼在這個區塊下方。")
    # TODO: 貼上您原本的持股監控程式碼

