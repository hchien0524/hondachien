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
    from portfolio_monitor import render_portfolio_monitor
    from backtest_engine import run_batch_backtest
    MODULES_LOADED = True
except ImportError as e:
    MODULES_LOADED = False
    st.error(f"模組匯入失敗: {e}。請確認所有 .py 檔案皆已建立。")

st.set_page_config(page_title="HIOS Wave Radar V26", layout="wide")

def main():
    st.title("🌊 HIOS Wave Radar V26 - 終極完全體")

    if not MODULES_LOADED:
        st.stop()

    # 1. 大盤風控儀表板
    try:
        render_market_dashboard()
    except Exception as e:
        st.warning(f"大盤風控模組載入中或發生錯誤: {e}")

    # 2. 側邊欄：戰術參數與戰情壓縮包
    st.sidebar.header("⚙️ 戰術參數設定")
    min_trust_buy = st.sidebar.number_input("投信買超下限 (張)", value=1000, step=100)
    max_bias = st.sidebar.number_input("MA20 乖離率上限 (%)", value=5.0, step=0.5)
    max_price = st.sidebar.number_input("股價上限 (元)", value=500, step=50)
    min_volume = st.sidebar.number_input("5日均量下限 (張)", value=1000, step=500)
    finmind_token = st.sidebar.text_input("🔑 FinMind Token (選填)", type="password")

    st.sidebar.markdown("---")
    st.sidebar.header("💾 實體戰情包 (防失憶)")
    
    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = []

    uploaded_json = st.sidebar.file_uploader("📥 匯入戰情包 (.json)", type="json")
    if uploaded_json is not None:
        try:
            st.session_state['portfolio'] = json.load(uploaded_json)
            st.sidebar.success("✅ 陣地恢復成功！")
        except:
            st.sidebar.error("❌ 檔案解析失敗")
                
    if st.session_state['portfolio']:
        json_str = json.dumps(st.session_state['portfolio'], indent=2)
        st.sidebar.download_button(
            label="💾 下載最新戰情包",
            data=json_str,
            file_name="hios_portfolio.json",
            mime="application/json"
        )

    # ==========================================
    # 3. 雙視窗核心架構
    # ==========================================
    tab1, tab2, tab3 = st.tabs(["🚀 雷達掃描室", "🛡️ 持股監控中心", "⏳ 時光機回測"])

    # --- 分頁一：雷達掃描室 ---
    with tab1:
        st.subheader("📂 籌碼資料匯入 (支援多選)")
        uploaded_files = st.file_uploader("請上傳三大法人 CSV 檔", type="csv", accept_multiple_files=True)

        if st.button("🚀 啟動終極深度掃描", type="primary"):
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

                        df_results = calculate_scores(df_clean, min_trust_buy, max_bias, max_price, min_volume, finmind_token)

                        if not df_results.empty:
                            st.markdown(f"### 🎯 掃描完成！共篩選出 {len(df_results)} 檔 S 級真龍")
                            
                            # 準備 Data Editor 的資料
                            df_display = df_results.copy()
                            df_display.insert(0, '加入監控', False)
                            
                            # 🃏 現代化 UI：使用 column_config 取代舊的 Pandas Styler
                            edited_df = st.data_editor(
                                df_display,
                                column_config={
                                    "加入監控": st.column_config.CheckboxColumn("📥 收編", default=False),
                                    "總分": st.column_config.ProgressColumn("🔥 總分", format="%.2f", min_value=0, max_value=250),
                                    "動能比例(%)": st.column_config.NumberColumn("🦅 動能(%)", format="%.2f %%"),
                                    "乖離率(%)": st.column_config.NumberColumn("乖離率(%)", format="%.2f %%"),
                                    "收盤價": st.column_config.NumberColumn("收盤價", format="%.2f"),
                                },
                                disabled=[col for col in df_display.columns if col != '加入監控'],
                                hide_index=True,
                                use_container_width=True
                            )

                            if st.button("➕ 將勾選標的加入監控中心", type="primary"):
                                selected_rows = edited_df[edited_df['加入監控'] == True]
                                if not selected_rows.empty:
                                    for _, row in selected_rows.iterrows():
                                        code = str(row['代號'])
                                        if not any(str(p.get('代號')) == code for p in st.session_state['portfolio']):
                                            st.session_state['portfolio'].append({
                                                "代號": code,
                                                "名稱": str(row['名稱']),
                                                "建倉價": float(row['收盤價']),
                                                "收盤價": float(row['收盤價'])
                                            })
                                    st.success(f"✅ 成功收編 {len(selected_rows)} 檔標的！請切換至「持股監控中心」查看。")
                                    st.rerun()
                                else:
                                    st.warning("⚠️ 請先在表格中勾選要收編的股票！")

                            save_capsule(df_results, "終極暴力評分", min_trust_buy, max_bias)
                        else:
                            st.warning("⚠️ 在目前的嚴格濾網下，沒有股票符合條件。")

    # --- 分頁二：持股監控中心 ---
    with tab2:
        try:
            render_portfolio_monitor()
        except Exception as e:
            st.error(f"監控中心發生錯誤: {e}")
            
    # --- 分頁三：時光機回測 ---
    with tab3:
        try:
            render_capsule_ui()
        except Exception as e:
            st.error(f"時光機發生錯誤: {e}")

if __name__ == "__main__":
    main()
