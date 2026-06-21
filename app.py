import streamlit as st
import pandas as pd
import json

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

st.set_page_config(page_title="HIOS Wave Radar V26.1", layout="wide")

def main():
    st.title("🌊 HIOS Wave Radar V26.1 - 族群共振版")

    if not MODULES_LOADED:
        st.stop()

    try:
        render_market_dashboard()
    except Exception as e:
        st.warning(f"大盤風控模組載入中或發生錯誤: {e}")

    st.sidebar.header("⚙️ 戰術參數設定")
    min_trust_buy = st.sidebar.number_input("投信買超下限 (張)", value=100, step=50)
    max_bias = st.sidebar.number_input("MA20 乖離率上限 (%)", value=5.0, step=0.5)
    max_price = st.sidebar.number_input("💰 最高股價上限 (元)", value=500.0, step=50.0)
    min_volume = st.sidebar.number_input("💧 最低 5 日均量 (張)", value=1000, step=500)
    finmind_token = st.sidebar.text_input("🔑 FinMind Token (選填)", type="password")

    st.sidebar.markdown("---")
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
                    st.sidebar.success("✅ 陣地恢復成功！")
                    st.rerun()
        except Exception as e:
            st.sidebar.error(f"❌ 讀取失敗: {e}")

    if st.session_state['portfolio']:
        json_str = json.dumps(st.session_state['portfolio'], ensure_ascii=False, indent=2)
        st.sidebar.download_button(label="💾 下載最新戰情包", data=json_str, file_name="HIOS_Portfolio.json", mime="application/json")

    tab1, tab2, tab3 = st.tabs(["🚀 雷達掃描室 (找飆股)", "🛡️ 持股監控中心 (顧陣地)", "⏳ V25 回測沙盒 (驗證勝率)"])

    with tab1:
        st.subheader("📂 籌碼資料匯入 (支援多選)")
        uploaded_files = st.file_uploader("請上傳三大法人 CSV 檔", type="csv", accept_multiple_files=True, key="radar_uploader")

        if st.button("🚀 啟動極簡暴力掃描", type="primary"):
            if not uploaded_files:
                st.warning("⚠️ 請先上傳至少一份 CSV 檔案！")
            else:
                with st.spinner(f"正在深度掃描 {len(uploaded_files)} 份檔案..."):
                    all_dfs = []
                    for f in uploaded_files:
                        df = parse_chip_csv(f)
                        if df is not None and not df.empty:
                            all_dfs.append(df)

                    if all_dfs:
                        df_clean = pd.concat(all_dfs, ignore_index=True)
                        df_clean = df_clean.groupby(['代號', '名稱'], as_index=False).sum()
                        st.session_state['latest_chip_data'] = df_clean
                        
                        df_results = calculate_scores(df_clean, min_trust_buy, max_bias, max_price, min_volume, finmind_token)
                        st.session_state['scan_results'] = df_results
                        st.success(f"✅ 成功匯入籌碼資料，共保留 {len(df_clean)} 檔純血普通股。")
                        
                        if not df_results.empty:
                            save_capsule(df_results, "極簡總分", min_trust_buy, max_bias)

        if 'scan_results' in st.session_state:
            df_results = st.session_state['scan_results']
            if not df_results.empty:
                st.markdown(f"### 🎯 掃描完成！共篩選出 {len(df_results)} 檔戰略目標 (已按總分排序)")
                df_display = df_results.copy()
                if '加入監控' not in df_display.columns:
                    df_display.insert(0, '加入監控', False)
                
                # 【更新】加入 產業類別 與 戰術標籤 的顯示格式
                styled_df = df_display.style.format({
                    "收盤價": "{:.2f}", "乖離率(%)": "{:.2f}", "5日均量(張)": "{:.0f}", "投信買賣超": "{:.0f}", 
                    "外資買賣超": "{:.0f}", "動能比例(%)": "{:.2f}", "連買天數": "{:.0f}", "🏆 總分": "{:.1f}"
                }).background_gradient(cmap='RdYlGn_r', subset=['乖離率(%)']).background_gradient(cmap='YlGn', subset=['🏆 總分'])
                
                edited_df = st.data_editor(styled_df, column_config={"加入監控": st.column_config.CheckboxColumn("📥 收編", default=False)}, disabled=[col for col in df_display.columns if col != '加入監控'], hide_index=True, use_container_width=True)
                
                if st.button("📥 將勾選標的加入監控中心", type="primary"):
                    selected_rows = edited_df[edited_df['加入監控'] == True]
                    if not selected_rows.empty:
                        for _, row in selected_rows.iterrows():
                            code = str(row['代號'])
                            if not any(str(item.get('代號', '')) == code for item in st.session_state['portfolio']):
                                st.session_state['portfolio'].append({"代號": code, "名稱": str(row['名稱']), "建倉價": float(row['收盤價']), "收盤價": float(row['收盤價'])})
                        st.success("✅ 成功加入監控中心！")
            else:
                st.warning("⚠️ 在目前的嚴格濾網下，沒有股票符合條件。")

        st.markdown("---")
        render_capsule_ui()

    with tab2:
        try:
            render_portfolio_monitor()
        except Exception as e:
            st.error(f"監控中心發生錯誤: {e}")

    with tab3:
        st.header("⏳ V25.3 戰術回測沙盒 (極簡版)")
        st.markdown("上傳過去某天的 CSV，系統將模擬當天買進，並嚴格執行 **「跌破 10MA 停損/停利」** 的紀律，為您結算真實勝率！")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            backtest_date = st.date_input("📅 選擇回測基準日 (CSV對應的日期)")
        with col2:
            bt_files = st.file_uploader("📂 上傳該日的法人 CSV 檔", type="csv", accept_multiple_files=True, key="bt_uploader")
            
        if st.button("⚙️ 啟動戰術時光機", type="primary"):
            if not bt_files:
                st.warning("請上傳歷史 CSV 檔案！")
            else:
                all_dfs = []
                for f in bt_files:
                    df = parse_chip_csv(f)
                    if df is not None and not df.empty:
                        all_dfs.append(df)
                        
                if all_dfs:
                    df_clean = pd.concat(all_dfs, ignore_index=True)
                    df_clean = df_clean.groupby(['代號', '名稱'], as_index=False).sum()
                    
                    date_str = backtest_date.strftime('%Y-%m-%d')
                    df_bt_results = run_batch_backtest(df_clean, date_str, min_trust_buy, max_bias, max_price, min_volume)
                    
                    if not df_bt_results.empty:
                        total_trades = len(df_bt_results)
                        win_trades = len(df_bt_results[df_bt_results['區間報酬(%)'] > 0])
                        win_rate = (win_trades / total_trades) * 100 if total_trades > 0 else 0
                        avg_return = df_bt_results['區間報酬(%)'].mean()
                        
                        st.markdown("---")
                        st.subheader("📊 戰術回測績效總結")
                        m1, m2, m3 = st.columns(3)
                        m1.metric("總交易檔數", f"{total_trades} 檔")
                        m2.metric("策略勝率 (賺錢比例)", f"{win_rate:.1f} %")
                        m3.metric("平均區間報酬", f"{avg_return:.2f} %")
                        
                        st.markdown("### 📜 逐筆交易明細")
                        styled_bt = df_bt_results.style.format({
                            "乖離率(%)": "{:.2f}", "進場價(隔日開盤)": "{:.2f}", "出場價": "{:.2f}", 
                            "最大漲幅(%)": "{:.2f}", "區間報酬(%)": "{:.2f}"
                        }).background_gradient(cmap='RdYlGn', subset=['區間報酬(%)'])
                        
                        st.dataframe(styled_bt, use_container_width=True, hide_index=True)
                    else:
                        st.warning("該日沒有符合條件的股票，或歷史股價抓取失敗。")

if __name__ == "__main__":
    main()
