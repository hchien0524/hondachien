import streamlit as st
import pandas as pd
import json

# 匯入模組 (加入全新的 state_manager)
try:
    from engine import parse_chip_csv  # 確保這裡對應您的 engine.py 或 data_engine.py
    from strategy_core import calculate_scores
    from time_capsule import save_capsule, render_capsule_ui
    from market_filter import render_market_dashboard
    from portfolio_monitor import render_portfolio_monitor
    from state_manager import GistManager  # 載入雲端記憶模組
    MODULES_LOADED = True
except ImportError as e:
    MODULES_LOADED = False
    st.error(f"模組匯入失敗: {e}。請確認所有 .py 檔案皆已建立。")

st.set_page_config(page_title="HIOS Wave Radar V24.2", layout="wide")

def main():
    st.title("🌊 HIOS Wave Radar V24.2 - 雲端記憶升級版")

    if not MODULES_LOADED:
        st.stop()

    # 1. 大盤風控儀表板
    try:
        render_market_dashboard()
    except Exception as e:
        st.warning(f"大盤風控模組載入中或發生錯誤: {e}")

    # 2. 側邊欄：戰術參數
    st.sidebar.header("⚙️ 戰術參數設定")
    strategy_mode = st.sidebar.radio("🧠 選擇大腦", ["雙大腦交集 (推薦)", "短波突擊大腦", "長線大底大腦"])
    min_trust_buy = st.sidebar.number_input("投信買超下限 (張)", value=100, step=50)
    max_bias = st.sidebar.number_input("MA20 乖離率上限 (%)", value=5.0, step=0.5)

    st.sidebar.markdown("---")
    
    # ==========================================
    # 🌟 V24.2 全新雲端記憶體 UI (取代 Base64)
    # ==========================================
    st.sidebar.header("☁️ 雲端記憶體 (防失憶)")
    
    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = []
    if 'gist_id' not in st.session_state:
        st.session_state['gist_id'] = ""

    github_token = st.sidebar.text_input("🔑 GitHub Token (必填)", type="password", help="請輸入您的 GitHub Personal Access Token")
    gist_id_input = st.sidebar.text_input("📂 Gist ID (若有舊紀錄請填入)", value=st.session_state['gist_id'])

    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("📥 載入陣地"):
            if github_token and gist_id_input:
                gm = GistManager(github_token)
                data = gm.load_data(gist_id_input, "portfolio.json")
                if data is not None:
                    st.session_state['portfolio'] = data
                    st.success("✅ 雲端陣地恢復成功！請查看持股監控中心。")
                else:
                    st.error("❌ 載入失敗，請檢查 Token 或 ID。")
            else:
                st.warning("請輸入 Token 與 Gist ID")
                
    with col2:
        if st.button("☁️ 同步雲端"):
            if github_token:
                if st.session_state['portfolio']:
                    gm = GistManager(github_token)
                    if gist_id_input:
                        gm.gist_id = gist_id_input
                    success = gm.save_data("portfolio.json", st.session_state['portfolio'])
                    if success:
                        st.success("✅ 同步成功！")
                        st.sidebar.info(f"📌 您的專屬 Gist ID:\n`{gm.gist_id}`\n請妥善保存此 ID！")
                    else:
                        st.error("❌ 同步失敗。")
                else:
                    st.warning("目前沒有持股可同步。")
            else:
                st.warning("請先輸入 GitHub Token！")

    # ==========================================
    # 3. 雙視窗核心架構 (Tabs)
    # ==========================================
    tab1, tab2 = st.tabs(["🚀 雷達掃描室 (找飆股)", "🛡️ 持股監控中心 (顧陣地)"])

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

    with tab2:
        try:
            render_portfolio_monitor()
        except Exception as e:
            st.error(f"監控中心發生錯誤: {e}")

if __name__ == "__main__":
    main()
