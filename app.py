import streamlit as st
import pandas as pd
import base64
import json

# 匯入模組
try:
    from data_engine import parse_chip_csv
    from strategy_core import calculate_scores
    from time_capsule import save_capsule, render_capsule_ui
    from market_filter import render_market_dashboard
    from portfolio_monitor import render_portfolio_monitor  # 新增 V24 監控模組
    MODULES_LOADED = True
except ImportError as e:
    MODULES_LOADED = False
    st.error(f"模組匯入失敗: {e}。請確認所有 .py 檔案皆已建立。")

st.set_page_config(page_title="HIOS Wave Radar V24", layout="wide")

def main():
    st.title("🌊 HIOS Wave Radar V24 - 雙視窗監控版")

    if not MODULES_LOADED:
        st.stop()

    # 1. 大盤風控儀表板 (全域顯示)
    try:
        render_market_dashboard()
    except Exception as e:
        st.warning(f"大盤風控模組載入中或發生錯誤: {e}")

    # 2. 側邊欄：戰術參數與戰情壓縮包
    st.sidebar.header("⚙️ 戰術參數設定")
    strategy_mode = st.sidebar.radio("🧠 選擇大腦", ["雙大腦交集 (推薦)", "短波突擊大腦", "長線大底大腦"])
    min_trust_buy = st.sidebar.number_input("投信買超下限 (張)", value=100, step=50)
    max_bias = st.sidebar.number_input("MA20 乖離率上限 (%)", value=5.0, step=0.5)

    st.sidebar.markdown("---")
    st.sidebar.header("💾 戰情壓縮包 (防失憶)")
    
    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = []

    import_code = st.sidebar.text_input("📥 匯入戰情包代碼 (Base64)")
    if st.sidebar.button("解碼並恢復陣地"):
        if import_code:
            try:
                decoded = base64.b64decode(import_code).decode('utf-8')
                st.session_state['portfolio'] = json.loads(decoded)
                st.sidebar.success("✅ 陣地恢復成功！請切換至「持股監控中心」查看。")
            except:
                st.sidebar.error("❌ 代碼無效，請確認複製完整。")
                
    if st.sidebar.button("📦 產生最新戰情包"):
        if st.session_state['portfolio']:
            json_str = json.dumps(st.session_state['portfolio'])
            encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
            st.sidebar.code(encoded, language="text")
            st.sidebar.info("請複製上方代碼並妥善保存。")
        else:
            st.sidebar.warning("目前沒有持股紀錄可打包。")

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
