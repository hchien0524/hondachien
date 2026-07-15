import streamlit as st
import pandas as pd
import io
from war_room_engine import WarRoomEngine
from broker_memory import BrokerMemory

st.set_page_config(page_title="HIOS V38 大一統量化中樞", layout="wide")

def init_modules():
    return WarRoomEngine(), BrokerMemory()

engine, memory = init_modules()

def read_taiwan_stock_csv(file_obj):
    content = file_obj.read()
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = content.decode('big5', errors='ignore')
        
    lines = text.split('\n')
    header_idx = 0
    for i, line in enumerate(lines):
        if '代號' in line or '證券代號' in line:
            header_idx = i
            break
            
    csv_data = '\n'.join(lines[header_idx:])
    df = pd.read_csv(io.StringIO(csv_data), thousands=',', on_bad_lines='skip')
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
    if st.button("📦 一鍵存檔並產生備份檔"):
        memory.save_all() 
        zip_buffer = memory.backup_to_zip()
        if zip_buffer:
            st.download_button(
                label="📥 點此下載 ZIP 備份",
                data=zip_buffer,
                file_name="HIOS_V38_Backup.zip",
                mime="application/zip"
            )
            st.success("備份檔已準備就緒！請點擊上方按鈕下載。")
        else:
            st.error("備份失敗，請確認資料庫狀態。")

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
                df = read_taiwan_stock_csv(f)
                if not df.empty:
                    df_list.append(df)
                
            with st.spinner("正在啟動全局資料湖與漏斗過濾..."):
                if df_list:
                    report_df = engine.process_chips(df_list)
                    st.session_state['latest_report'] = report_df
                else:
                    st.error("無法解析上傳的 CSV 檔案，請確認檔案內容。")
    
    if 'latest_report' in st.session_state and not st.session_state['latest_report'].empty:
        df = st.session_state['latest_report'].copy()
        
        if filter_value: df = df[df['戰略標籤'].str.contains("🛡️ 價值防禦")]
        if filter_bottom: df = df[df['戰略標籤'].str.contains("📉 底部打底")]
        if filter_ignition: df = df[df['戰略標籤'].str.contains("🔥 動能爆發")]
        if filter_nohigh: df = df[df['戰略標籤'].str.contains("🛑 未創高")]
            
        st.success(f"掃描完成！符合目前濾網條件共 {len(df)} 檔")
        st.dataframe(df, use_container_width=True)
        
        # 🚨 批次狙擊目標鎖定與傳送
        st.markdown("---")
        st.subheader("🎯 鎖定狙擊目標 (支援批次傳送)")
        if not df.empty:
            target_options = (df['代號'].astype(str) + " " + df['名稱']).tolist()
            default_selections = target_options[:3] if len(target_options) >= 3 else target_options
            selected_targets = st.multiselect("請選擇要進行 X 光掃描的標的 (可複選)：", target_options, default=default_selections)
            
            if st.button("🔫 批次傳送至 X 光狙擊室"):
                if selected_targets:
                    target_codes = [t.split(" ")[0] for t in selected_targets]
                    st.session_state['sniper_targets'] = target_codes
                    st.success(f"已成功鎖定 {len(target_codes)} 檔目標！請點擊上方「🔬 階段三：X光狙擊」分頁進行解剖。")
                else:
                    st.warning("請至少選擇一檔標的！")
                
    elif 'latest_report' in st.session_state:
        st.warning("⚠️ 目前濾網條件下無符合標的，請嘗試放寬左側標籤條件。")
    else:
        st.info("請於左側上傳 CSV 並點擊啟動掃描。")

with tab3:
    st.header("🔬 主力 X 光狙擊室")
    if 'sniper_targets' in st.session_state and st.session_state['sniper_targets']:
        targets = st.session_state['sniper_targets']
        st.success(f"🎯 當前鎖定批次目標：【 {', '.join(targets)} 】")
        
        try:
            from yahoo_sniper import YahooSniper
            sniper = YahooSniper()
            
            for code in targets:
                st.markdown(f"### 🎯 標的：{code}")
                sniper.render_ui(target_code=code) 
                st.markdown("---")
                
        except ImportError:
            st.error("⚠️ 找不到 `yahoo_sniper.py` 檔案！請確認該檔案是否存在於您的 GitHub 中。")
        except Exception as e:
            st.error(f"⚠️ 執行狙擊模組時發生錯誤：{e}")
            
    else:
        st.warning("⚠️ 尚未鎖定目標。請先在「階段二：終極戰報」中選擇標的並點擊傳送。")

with tab4:
    # 🚨 階段四完全解封，呼叫 broker_memory.py 的 UI 介面
    st.header("📁 歷史記憶與持股管理")
    memory.render_ui()
