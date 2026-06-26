import streamlit as st
import pandas as pd
import json
import portfolio_monitor

try:
    import strategy_core
except ImportError:
    strategy_core = None

try:
    import backtest_engine
except ImportError:
    backtest_engine = None

# 🛡️ 載入大盤風控模組
try:
    import market_filter
except ImportError:
    market_filter = None

st.set_page_config(
    page_title="HIOS Wave Radar V29.4",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.sidebar.title("🎯 HIOS Wave Radar")
    st.sidebar.caption("V29.4 終極雙腦 + 大盤風控版")
    
    st.sidebar.header("📂 1. 數據引擎")
    uploaded_csvs = st.sidebar.file_uploader(
        "上傳法人買賣超 CSV (支援多檔歷史資料)", 
        type=['csv'], 
        accept_multiple_files=True
    )
    
    st.sidebar.header("⚙️ 2. 動態濾網設定")
    filter_vol_min = st.sidebar.number_input("💧 5日均量下限 (張)", min_value=0, max_value=20000, value=3000, step=500, help="過濾掉流動性差的冷門股")
    filter_bias_max = st.sidebar.number_input("🔥 月線乖離率上限 (%)", min_value=1.0, max_value=50.0, value=5.0, step=0.5, help="拒絕追高，過濾掉漲多乖離過大的危險股")
    filter_resonance = st.sidebar.checkbox("🤝 嚴格族群濾網 (共振 >= 3)", value=True)
    
    st.sidebar.markdown("---")
    st.sidebar.header("💾 3. 戰情包管理")

    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = []

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
    
    # 🛡️ V29.4 新增：將大盤風控加入第一個 Tab
    tab0, tab1, tab2, tab3 = st.tabs(["🚦 大盤風控", "🚀 雷達掃描室", "🛡️ 持股監控中心", "⏳ 時光膠囊 (AI 回測)"])
    
    with tab0:
        if market_filter:
            try:
                market_filter.render_market_dashboard()
            except Exception as e:
                st.error(f"大盤風控模組執行錯誤: {e}")
        else:
            st.warning("⚠️ 找不到 `market_filter.py`，請確認大盤風控模組檔案存在。")

    with tab1:
        if uploaded_csvs and len(uploaded_csvs) > 0:
            if strategy_core:
                try:
                    strategy_core.run_radar(uploaded_csvs, filter_bias_max, filter_resonance, filter_vol_min)
                except Exception as e:
                    st.error(f"雷達運算發生錯誤: {e}")
            else:
                st.warning("⚠️ 找不到 `strategy_core.py`，請確認核心邏輯檔案存在。")
        else:
            st.header("🚀 雷達掃描室 (雙腦評分系統)")
            st.info("👈 請先從左側邊欄上傳「法人買賣超 CSV (可多選)」以啟動雷達。")
            
    with tab2:
        portfolio_monitor.render_portfolio_monitor()

    with tab3:
        if backtest_engine:
            backtest_engine.render_time_capsule()
        else:
            st.warning("⚠️ 找不到 `backtest_engine.py`，請確認回測引擎檔案存在。")

if __name__ == "__main__":
    main()
