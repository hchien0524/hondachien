import streamlit as st
import pandas as pd
import json

# 匯入模組
try:
    from data_engine import parse_chip_csv  
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
    st.title("🌊 HIOS Wave Radar V24.2 - 投顧級戰術分群版")

    if not MODULES_LOADED:
        st.stop()

    # 1. 大盤風控儀表板
    try:
        render_market_dashboard()
    except Exception as e:
        st.warning(f"大盤風控模組載入中或發生錯誤: {e}")

    # 2. 側邊欄：戰術參數設定 (已移除選擇大腦，改為一鍵全掃)
    st.sidebar.header("⚙️ 戰術參數設定")
    st.sidebar.info("💡 已升級為「一鍵全掃」架構，系統將自動為您進行戰術分群，極限節省 API 額度。")
    min_trust_buy = st.sidebar.number_input("投信買超下限 (張)", value=100, step=50)
    max_bias = st.sidebar.number_input("MA20 乖離率上限 (%)", value=5.0, step=0.5)
    
    finmind_token = st.sidebar.text_input("🔑 FinMind Token (選填，防封鎖)", type="password", help="免費註冊 FinMind 取得 Token 可大幅提升掃描速度與穩定度")

    st.sidebar.markdown("---")
    
    # 實體戰情包 (防失憶)
    st.sidebar.header("💾 實體戰情包 (防失憶)")
    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = []

    uploaded_portfolio = st.sidebar.file_uploader("📥 匯入舊陣地 (上傳 JSON 檔)", type=['json'])
    if uploaded_portfolio is not None:
        try:
            portfolio_data = json.load(uploaded_portfolio)
            if isinstance(portfolio_data, list):
                if st.sidebar.button("⚠️ 確認覆蓋目前陣地", type="primary"):
                    st.session_state['portfolio'] = portfolio_data
                    st.sidebar.success("✅ 陣地恢復成功！請查看持股監控中心。")
                    st.rerun()
            else:
                st.sidebar.error("❌ 檔案格式錯誤，請上傳正確的戰情包。")
        except Exception as e:
            st.sidebar.error(f"❌ 讀取失敗: {e}")

    st.sidebar.markdown("---")

    if st.session_state['portfolio']:
        json_str = json.dumps(st.session_state['portfolio'], ensure_ascii=False, indent=2)
        st.sidebar.download_button(
            label="💾 下載最新戰情包 (備份)",
            data=json_str,
            file_name="HIOS_Portfolio.json",
            mime="application/json"
        )
    else:
        st.sidebar.warning("目前沒有持股可備份。")

    # 3. 雙視窗核心架構
    tab1, tab2 = st.tabs(["🚀 雷達掃描室 (找飆股)", "🛡️ 持股監控中心 (顧陣地)"])

    with tab1:
        st.subheader("📂 籌碼資料匯入 (支援多選)")
        uploaded_files = st.file_uploader("請上傳三大法人 CSV 檔", type="csv", accept_multiple_files=True)

        if st.button("🚀 啟動全域戰術掃描", type="primary"):
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
                        df_clean = df_clean.groupby(['代號', '名稱'], as_index=False).sum()
                        st.session_state['latest_chip_data'] = df_clean
                        
                        # 【關鍵修改】：移除 strategy_mode，改為一鍵全掃
                        df_results = calculate_scores(df_clean, min_trust_buy, max_bias, finmind_token)
                        
                        st.session_state['scan_results'] = df_results
                        st.success(f"✅ 成功匯入籌碼資料，共保留 {len(df_clean)} 檔純血普通股。")
                        
                        if not df_results.empty:
                            # 為了相容舊版時光膠囊，硬塞一個 "一鍵全掃" 作為策略名稱
                            save_capsule(df_results, "一鍵全掃", min_trust_buy, max_bias)

        # 顯示掃描結果與一鍵收編 UI
        if 'scan_results' in st.session_state:
            df_results = st.session_state['scan_results']
            
            if not df_results.empty:
                st.markdown(f"### 🎯 掃描完成！共篩選出 {len(df_results)} 檔戰略目標")
                
                df_display = df_results.copy()
                if '加入監控' not in df_display.columns:
                    df_display.insert(0, '加入監控', False)
                
                # 針對新欄位進行 UI 格式化優化 (加入爆發力與防禦力)
                styled_df = df_display.style.format({
                    "收盤價": "{:.2f}", "乖離率(%)": "{:.2f}",
                    "投信買賣超": "{:.0f}", "外資買賣超": "{:.0f}", 
                    "🔥 爆發力": "{:.1f}", "🛡️ 防禦力": "{:.1f}",
                    "動能比例(%)": "{:.2f}", "連買天數": "{:.0f}"
                }).background_gradient(cmap='RdYlGn_r', subset=['乖離率(%)']) \
                  .background_gradient(cmap='YlOrRd', subset=['🔥 爆發力']) \
                  .background_gradient(cmap='YlGn', subset=['🛡️ 防禦力'])
                
                edited_df = st.data_editor(
                    styled_df,
                    column_config={
                        "加入監控": st.column_config.CheckboxColumn("📥 收編", default=False)
                    },
                    disabled=[col for col in df_display.columns if col != '加入監控'],
                    hide_index=True,
                    use_container_width=True,
                    key="radar_data_editor"
                )
                
                if st.button("📥 將勾選標的加入監控中心", type="primary"):
                    selected_rows = edited_df[edited_df['加入監控'] == True]
                    if selected_rows.empty:
                        st.warning("⚠️ 請先在表格中勾選要收編的股票！")
                    else:
                        added_count = 0
                        for _, row in selected_rows.iterrows():
                            code = str(row['代號'])
                            name = str(row['名稱'])
                            price = float(row['收盤價'])
                            
                            exists = any(str(item.get('代號', '')) == code for item in st.session_state['portfolio'])
                            if not exists:
                                st.session_state['portfolio'].append({
                                    "代號": code, "名稱": name, "建倉價": price, "收盤價": price
                                })
                                added_count += 1
                                
                        if added_count > 0:
                            st.success(f"✅ 成功將 {added_count} 檔標的加入監控中心！請切換分頁查看。")
                        else:
                            st.info("💡 勾選的標的已經在監控中心了。")
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
