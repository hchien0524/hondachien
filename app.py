import streamlit as st
import pandas as pd
import io
from war_room_engine import WarRoomEngine

st.set_page_config(page_title="HIOS V38 大一統量化中樞", layout="wide")

# 初始化模組
@st.cache_resource
def init_modules():
    return WarRoomEngine()

engine = init_modules()

def read_taiwan_stock_csv(file_obj):
    """台股專用 CSV 防彈讀取器：自動跳過無用標題、備註，並處理編碼與逗號"""
    content = file_obj.read()
    
    # 1. 破解編碼地雷
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = content.decode('big5', errors='ignore')
        
    lines = text.split('\n')
    
    # 2. 破解頭部地雷：尋找真正的標題行
    header_idx = 0
    for i, line in enumerate(lines):
        if '代號' in line or '證券代號' in line:
            header_idx = i
            break
            
    # 將真正有用的資料重新組合
    csv_data = '\n'.join(lines[header_idx:])
    
    # 3. 破解尾部與數字地雷：thousands=',' 處理數字逗號，on_bad_lines='skip' 略過尾部備註
    df = pd.read_csv(io.StringIO(csv_data), thousands=',', on_bad_lines='skip')
    
    # 清理欄位名稱（去除多餘空白與引號）
    df.columns = [str(c).strip().replace('"', '').replace('=', '') for c in df.columns]
    
    return df

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
            df_list = []
            for f in uploaded_files:
                # 使用我們特製的防彈讀取器
                df = read_taiwan_stock_csv(f)
                if not df.empty:
                    df_list.append(df)
                
            with st.spinner("正在啟動全局資料湖與漏斗過濾..."):
                if df_list:
                    report_df = engine.process_chips(df_list)
                    st.session_state['latest_report'] = report_df
                else:
                    st.error("無法解析上傳的 CSV 檔案，請確認檔案內容。")
    
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
