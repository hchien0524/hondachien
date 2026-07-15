import streamlit as st
import pandas as pd
import io
from war_room_engine import WarRoomEngine

st.set_page_config(page_title="HIOS V38 大一統量化中樞", layout="wide")

# 初始化模組 (暫時移除 BrokerMemory 以解除封印)
@st.cache_resource
def init_modules():
    return WarRoomEngine()

engine = init_modules()

# --- 左側邊欄：戰略控制台 ---
with st.sidebar:
    st.title("🦅 HIOS V38 戰略控制台")
    st.markdown("---")
    
    st.header("📁 1. 籌碼資料上傳")
    uploaded_files = st.file_uploader("上傳近 N 日法人買賣超 CSV", type="csv", accept_multiple_files=True)
    
    st.markdown("---")
    st.header("⚙️ 2. 動態標籤濾網")
    st.caption("勾選以過濾戰報顯示內容 (可複選)")
    filter_value = st.checkbox("🛡️ 價值防禦 (PE < 15)", value=False)
    filter_bottom = st.checkbox("📉 底部打底 (季線 ±5%)", value=False)
    filter_ignition = st.checkbox("🔥 動能爆發 (點火 > 3倍)", value=False)
    filter_nohigh = st.checkbox("🛑 未創高 (避開過熱)", value=False)
    
    st.markdown("---")
    st.header("💾 3. 系統防呆備份")
    st.info("備份模組建置中... (暫時解除封印)")
    # if st.button("📦 一鍵存檔並產生備份檔"):
    #     memory.save_all() # 強制存檔
    #     zip_buffer = memory.backup_to_zip()
    #     if zip_buffer:
    #         st.download_button(
    #             label="📥 點此下載 ZIP 備份",
    #             data=zip_buffer,
    #             file_name="HIOS_V38_Backup.zip",
    #             mime="application/zip"
    #         )
    #         st.success("備份檔已準備就緒！")

# --- 主畫面：4 大作戰階段 ---
st.title("HIOS V38 終極量化交易中樞")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 階段一：宏觀資金 (族群)", 
    "🎯 階段二：終極戰報 (雷達)", 
    "🔬 階段三：X光狙擊 (分點)", 
    "📁 階段四：歷史與持股"
])

with tab1:
    st.header("📊 宏觀資金流向")
    st.info("此處介接 sector_flow_radar.py (族群資金雷達)")

with tab2:
    st.header("🎯 終極戰報：標籤賦能雷達")
    if uploaded_files:
        if st.button("🚀 啟動 V38 全局掃描"):
            df_list = [pd.read_csv(f) for f in uploaded_files]
            with st.spinner("正在啟動全局資料湖與漏斗過濾..."):
                report_df = engine.process_chips(df_list)
                st.session_state['latest_report'] = report_df
    
    # 顯示與過濾戰報
    if 'latest_report' in st.session_state and not st.session_state['latest_report'].empty():
        df = st.session_state['latest_report'].copy()
        
        # 根據左側邊欄的勾選進行動態過濾
        if filter_value:
            df = df[df['戰略標籤'].str.contains("🛡️ 價值防禦")]
        if filter_bottom:
            df = df[df['戰略標籤'].str.contains("📉 底部打底")]
        if filter_ignition:
            df = df[df['戰略標籤'].str.contains("🔥 動能爆發")]
        if filter_nohigh:
            df = df[df['戰略標籤'].str.contains("🛑 未創高")]
            
        st.success(f"掃描完成！符合目前濾網條件共 {len(df)} 檔")
        st.dataframe(df, use_container_width=True)
    elif 'latest_report' in st.session_state:
        st.warning("⚠️ 目前濾網條件下無符合標的，請嘗試放寬左側標籤條件。")
    else:
        st.info("請於左側上傳 CSV 並點擊啟動掃描。")

with tab3:
    st.header("🔬 主力 X 光狙擊室")
    st.info("此處介接 yahoo_sniper.py (分點券商追蹤)")

with tab4:
    st.header("📁 歷史記憶與持股管理")
    st.info("此處介接 broker_memory.py (資料庫管理)")
