import streamlit as st
import pandas as pd
import json

# 匯入模組
try:
    from data_engine import parse_chip_csv  # 確保這裡對應您的檔案名稱 (data_engine.py)
    from strategy_core import calculate_scores
    from time_capsule import save_capsule, render_capsule_ui
    from market_filter import render_market_dashboard
    from portfolio_monitor import render_portfolio_monitor
    MODULES_LOADED = True
except ImportError as e:
    MODULES_LOADED = False
    st.error(f"模組匯入失敗: {e}。請確認所有 .py 檔案皆已建立。")

st.set_page_config(page_title="HIOS Wave Radar V24.2", layout="wide")

def main():
    st.title("🌊 HIOS Wave Radar V24.2 - 實體戰情包升級版")

    if not MODULES_LOADED:
        st.stop()

    # 1. 大盤風控儀表板 (全域顯示)
    try:
        render_market_dashboard()
    except Exception as e:
        st.warning(f"大盤風控模組載入中或發生錯誤: {e}")

    # 2. 側邊欄：戰術參數設定
    st.sidebar.header("⚙️ 戰術參數設定")
    strategy_mode = st.sidebar.radio("🧠 選擇大腦", ["雙大腦交集 (推薦)", "短波突擊大腦", "長線大底大腦"])
    min_trust_buy = st.sidebar.number_input("投信買超下限 (張)", value=100, step=50)
    max_bias = st.sidebar.number_input("MA20 乖離率上限 (%)", value=5.0, step=0.5)

    st.sidebar.markdown("---")
    
    # ==========================================
    # 🌟 V24.2 實體戰情包 (本地 JSON 檔案管理)
    # ==========================================
    st.sidebar.header("💾 實體戰情包 (防失憶)")
    
    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = []

    # 1. 匯入戰情包 (上傳 JSON)
    uploaded_portfolio = st.sidebar.file_uploader("📥 匯入舊陣地 (上傳 JSON 檔)", type=['json'])
    if uploaded_portfolio is not None:
        try:
            # 讀取並解析 JSON
            portfolio_data = json.load(uploaded_portfolio)
            
            # 防呆：確認上傳的檔案格式正確
            if isinstance(portfolio_data, list):
                # 只有當目前陣地為空，或者使用者按下確認時才覆蓋，避免誤觸
                if st.sidebar.button("⚠️ 確認覆蓋目前陣地", type="primary"):
                    st.session_state['portfolio'] = portfolio_data
                    st.sidebar.success("✅ 陣地恢復成功！請查看持股監控中心。")
                    st.rerun()
            else:
                st.sidebar.error("❌ 檔案格式錯誤，請上傳正確的戰情包。")
        except Exception as e:
            st.sidebar.error(f"❌ 讀取失敗: {e}")

    st.sidebar.markdown("---")

    # 2. 匯出戰情包 (下載 JSON)
    if st.session_state['portfolio']:
        # 將目前的陣地資料轉成 JSON 字串
        json_str = json.dumps(st.session_state['portfolio'], ensure_ascii=False, indent=2)
        
        st.sidebar.download_button(
            label="💾 下載最新戰情包 (備份)",
            data=json_str,
            file_name="HIOS_Portfolio.json",
            mime="application/json",
            help="請在關閉網頁前下載此檔案，下次開啟時上傳即可恢復陣地。"
        )
    else:
        st.sidebar.warning("目前沒有持股可備份。")

    # ==========================================
    # 3. V24 雙視窗核心架構 (Tabs)
    # ==========================================
    tab1, tab2 = st.tabs(["🚀 雷達掃描室 (找飆股)", "🛡️ 持股監控中心 (顧陣地)"])

    # --- 分頁一：雷達掃描室 ---
    with tab1:
        st.subheader("📂 籌碼資料匯入 (支援多選)")
        uploaded_files = st.file_uploader("請上傳三大法人 CSV 檔", type="csv", accept_multiple_files=True)

        if st.button("🚀 啟動雙大腦深度掃描", type="primary"):
            if not uploaded_files:
                st.warning("⚠️ 請先上傳至少一份 CSV 檔案！")
            else:
                with st.spinner(f"正在深度掃描 {len(uploaded_files)} 份檔案..."):
                    all_dfs = []
                    for f in uploaded_files:
                        df = parse_chip_csv(f)
                        if df is not None and not df.empty:
                            all_dfs.append(df)

                    if not all_dfs:
                        st.error("❌ 找不到符合的資料，請確認 CSV 格式。")
                    else:
                        df_clean = pd.concat(all_dfs, ignore_index=True)
                        # 【關鍵】：將清洗好的籌碼存入 session_state，讓監控中心可以讀取！
                        st.session_state['latest_chip_data'] = df_clean
                        
                        st.success(f"✅ 成功匯入籌碼資料，共保留 {len(df_clean)} 檔純血普通股。")

                        df_results = calculate_scores(df_clean, min_trust_buy, max_bias, strategy_mode)

                        if not df_results.empty:
                            st.markdown(f"### 🎯 掃描完成！共篩選出 {len(df_results)} 檔 S 級真龍")
                            try:
                                styled_df = df_results.style.format({
                                    "收盤價": "{:.2f}", "MA20": "{:.2f}", "乖離率(%)": "{:.2f}",
                                    "投信買賣超": "{:.0f}", "外資買賣超": "{:.0f}", "總分": "{:.2f}"
                                }).background_gradient(cmap='RdYlGn_r', subset=['乖離率(%)']) \
                                  .background_gradient(cmap='YlGn', subset=['總分'])
                                st.dataframe(styled_df, use_container_width=True, hide_index=True)
                            except:
                                st.dataframe(df_results, use_container_width=True, hide_index=True)

                            save_capsule(df_results, strategy_mode, min_trust_buy, max_bias)
                        else:
                            st.warning("⚠️ 在目前的嚴格濾網下，沒有股票符合條件。")

        st.markdown("---")
        render_capsule_ui()

    # --- 分頁二：持股監控中心 ---
    with tab2:
        try:
            render_portfolio_monitor()
        except Exception as e:
            st.error(f"監控中心發生錯誤: {e}")

if __name__ == "__main__":
    main()
