import streamlit as st
import pandas as pd
import json
import portfolio_monitor
# 若有獨立的 strategy_core.py，請確保它在同一個資料夾下
try:
    import strategy_core
except ImportError:
    strategy_core = None

# ==========================================
# ⚙️ 系統全域設定
# ==========================================
st.set_page_config(
    page_title="HIOS Wave Radar V27.1",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    # ==========================================
    # 🎛️ 左側邊欄 (Sidebar) 控制中心
    # ==========================================
    st.sidebar.title("🎯 HIOS Wave Radar")
    st.sidebar.caption("V27.1 輕量化量化交易系統")
    
    st.sidebar.header("📂 1. 數據引擎")
    uploaded_csv = st.sidebar.file_uploader("上傳今日法人買賣超 CSV", type=['csv'])
    
    st.sidebar.header("⚙️ 2. 嚴格濾網設定")
    filter_momentum = st.sidebar.checkbox("🔥 嚴格動能濾網 (動能 > 0.2%)", value=True)
    filter_resonance = st.sidebar.checkbox("🤝 嚴格族群濾網 (共振 >= 3)", value=True)
    filter_liquidity = st.sidebar.checkbox("💧 鐵血流動性 (5日均量 > 1000)", value=True)
    
    # ==========================================
    # 💾 3. 戰情包管理區塊 (JSON 存取)
    # ==========================================
    st.sidebar.markdown("---")
    st.sidebar.header("💾 3. 戰情包管理")

    # 確保 session_state 中有 portfolio
    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = []

    # (A) 儲存最新戰情包
    if len(st.session_state['portfolio']) > 0:
        portfolio_json = json.dumps(st.session_state['portfolio'], ensure_ascii=False, indent=2)
        st.sidebar.download_button(
            label="⬇️ 儲存最新戰情包",
            data=portfolio_json,
            file_name="portfolio_backup.json",
            mime="application/json",
            use_container_width=True
        )
    else:
        st.sidebar.button("⬇️ 儲存最新戰情包", disabled=True, help="目前沒有持股可供儲存", use_container_width=True)

    # (B) 載入本機戰情包
    uploaded_file = st.sidebar.file_uploader("⬆️ 載入本機戰情包 (.json)", type=['json'])
    if uploaded_file is not None:
        try:
            loaded_data = json.load(uploaded_file)
            if st.sidebar.button("⚠️ 確認載入 (將覆蓋目前畫面)", type="primary", use_container_width=True):
                st.session_state['portfolio'] = loaded_data
                st.sidebar.success("✅ 戰情包載入成功！")
                st.rerun()
        except Exception as e:
            st.sidebar.error("檔案解析失敗，請確認是否為正確的 JSON 檔。")

    # ==========================================
    # 🖥️ 主畫面雙分頁 (Tabs)
    # ==========================================
    tab1, tab2 = st.tabs(["🚀 雷達掃描室", "🛡️ 持股監控中心"])
    
    # --- 分頁 1：雷達掃描室 ---
    with tab1:
        if uploaded_csv is not None:
            if strategy_core:
                # 這裡呼叫您的 strategy_core 進行運算
                # 假設您的 strategy_core 有一個主函數，例如 run_radar
                try:
                    st.info("📡 正在啟動 CSV 內部迴圈與雙腦評分系統...")
                    # strategy_core.run_radar(uploaded_csv, filter_momentum, filter_resonance, filter_liquidity)
                    st.success("✅ 雷達掃描完成！(請依據您的 strategy_core 實際函數名稱進行串接)")
                except Exception as e:
                    st.error(f"雷達運算發生錯誤: {e}")
            else:
                st.warning("⚠️ 找不到 `strategy_core.py`，請確認核心邏輯檔案存在。")
        else:
            st.info("👈 請先從左側邊欄上傳今日的「法人買賣超 CSV」以啟動雷達。")
            
    # --- 分頁 2：持股監控中心 ---
    with tab2:
        # 直接呼叫我們剛剛完美竣工的 V27.1 戰情卡片版
        portfolio_monitor.render_portfolio_monitor()

if __name__ == "__main__":
    main()
