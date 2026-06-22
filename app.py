import streamlit as st
import pandas as pd
import json
import os
import re

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

st.set_page_config(page_title="HIOS Wave Radar V27", layout="wide")

# 實體戰情包檔案路徑
LOCAL_PORTFOLIO_FILE = "local_portfolio.json"

def load_local_portfolio():
    if os.path.exists(LOCAL_PORTFOLIO_FILE):
        try:
            with open(LOCAL_PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_local_portfolio(portfolio_data):
    with open(LOCAL_PORTFOLIO_FILE, 'w', encoding='utf-8') as f:
        json.dump(portfolio_data, f, ensure_ascii=False, indent=4)

def main():
    st.title("🌊 HIOS Wave Radar V27 - 全自動狙擊版")

    if not MODULES_LOADED:
        st.stop()

    # 1. 大盤風控儀表板
    try:
        render_market_dashboard()
    except Exception as e:
        st.warning(f"大盤風控模組載入中或發生錯誤: {e}")

    # 2. 側邊欄：戰術參數與濾網
    st.sidebar.header("⚙️ 基礎戰術參數")
    min_trust_buy = st.sidebar.number_input("投信買超下限 (張)", value=1000, step=500)
    max_bias = st.sidebar.number_input("MA20 乖離率上限 (%)", value=5.0, step=1.0)
    max_price = st.sidebar.number_input("股價上限 (元)", value=500, step=50)
    min_volume = st.sidebar.number_input("5日均量下限 (張)", value=1000, step=500)
    
    st.sidebar.markdown("---")
    st.sidebar.header("🛡️ 高階勝率濾網 (V27 實戰版)")
    strict_momentum = st.sidebar.checkbox("🔥 嚴格動能濾網 (動能 > 0.2%)", value=True, help="過濾掉投信買盤力道不足的標的，只留主力強攻股。")
    strict_resonance = st.sidebar.checkbox("🤝 嚴格族群濾網 (共振 >= 3檔)", value=True, help="過濾掉單兵突擊的冷門股，只做市場資金主旋律。")

    st.sidebar.markdown("---")
    st.sidebar.header("💾 實體戰情包 (防失憶)")
    
    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = load_local_portfolio()

    if st.sidebar.button("📥 載入本機戰情包"):
        st.session_state['portfolio'] = load_local_portfolio()
        st.sidebar.success("✅ 陣地恢復成功！")
            
    if st.sidebar.button("💾 儲存最新戰情包"):
        save_local_portfolio(st.session_state['portfolio'])
        st.sidebar.success("✅ 陣地已安全備份至本機！")

    # ==========================================
    # 3. 雙視窗核心架構 (Tabs)
    # ==========================================
    tab1, tab2, tab3 = st.tabs(["🚀 雷達掃描室 (找飆股)", "🛡️ 持股監控中心 (顧陣地)", "⏳ 時光膠囊 (回測)"])

    # --- 分頁一：雷達掃描室 ---
    with tab1:
        st.subheader("📂 籌碼資料匯入 (支援多選 1~3 天)")
        uploaded_files = st.file_uploader("請上傳三大法人 CSV 檔", type="csv", accept_multiple_files=True)

        if st.button("🚀 啟動全域深度掃描", type="primary"):
            if not uploaded_files:
                st.warning("⚠️ 請先上傳至少一份 CSV 檔案！")
            else:
                with st.spinner(f"正在深度聚合 {len(uploaded_files)} 份檔案..."):
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
                        
                        st.success(f"✅ 成功匯入籌碼資料，共保留 {len(df_clean)} 筆純血普通股紀錄。")

                        # 呼叫核心引擎
                        df_results = calculate_scores(df_clean, min_trust_buy, max_bias, max_price, min_volume)

                        if not df_results.empty:
                            # ---------------------------------------------------------
                            # 🛡️ V27 鐵血濾網執行區
                            # ---------------------------------------------------------
                            df_display = df_results.copy()
                            
                            if strict_momentum and '動能比例' in df_display.columns:
                                df_display = df_display[df_display['動能比例'] > 0.2]
                                
                            if strict_resonance and '戰術標籤' in df_display.columns:
                                def check_resonance(tag):
                                    if '族群共振' in str(tag):
                                        match = re.search(r'\((\d+)檔\)', str(tag))
                                        if match:
                                            return int(match.group(1)) >= 3
                                    return False
                                df_display = df_display[df_display['戰術標籤'].apply(check_resonance)]
                            
                            if df_display.empty:
                                st.warning("⚠️ 原始名單有股票，但被「高階勝率濾網」全數無情秒殺！請放寬濾網或等待更好的時機。")
                            else:
                                st.markdown(f"### 🎯 掃描完成！原始 {len(df_results)} 檔 ➔ 終極精煉 **{len(df_display)}** 檔超級菁英")
                                
                                df_display.insert(0, '加入監控', False)
                                
                                # 現代化進度條 UI
                                styled_df = df_display.style.format({
                                    "收盤價": "{:.2f}", "乖離率(%)": "{:.2f}",
                                    "投信買賣超": "{:.0f}", "外資買賣超": "{:.0f}", 
                                    "5日均量": "{:.0f}", "動能比例": "{:.2f}", "總分": "{:.2f}"
                                }).bar(subset=['總分'], color='#00cc66', vmin=0) \
                                  .bar(subset=['動能比例'], color='#ff9900', vmin=0) \
                                  .background_gradient(cmap='RdYlGn_r', subset=['乖離率(%)'])
                                
                                edited_df = st.data_editor(
                                    styled_df, 
                                    column_config={
                                        "加入監控": st.column_config.CheckboxColumn("📥 收編", default=False)
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
                                            if not any(str(item.get('代號', '')) == code for item in st.session_state['portfolio']):
                                                st.session_state['portfolio'].append({
                                                    "代號": code,
                                                    "名稱": row['名稱'],
                                                    "建倉價": float(row['收盤價']),
                                                    "收盤價": float(row['收盤價'])
                                                })
                                        save_local_portfolio(st.session_state['portfolio'])
                                        st.success(f"✅ 成功收編 {len(selected_rows)} 檔真龍！已自動備份至本機。")
                                        st.rerun()
                                    else:
                                        st.warning("請先勾選要收編的股票！")

                                save_capsule(df_display, "全自動狙擊", min_trust_buy, max_bias)
                        else:
                            st.warning("⚠️ 在目前的基礎參數下，沒有股票符合條件。")

    # --- 分頁二：持股監控中心 ---
    with tab2:
        try:
            render_portfolio_monitor()
        except Exception as e:
            st.error(f"監控中心發生錯誤: {e}")
            
    # --- 分頁三：時光膠囊 ---
    with tab3:
        try:
            render_capsule_ui()
        except Exception as e:
            st.error(f"時光膠囊發生錯誤: {e}")

if __name__ == "__main__":
    main()
