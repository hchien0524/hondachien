import streamlit as st
import pandas as pd
import json
import time
import random
from datetime import datetime

# ==========================================
# 🛡️ 模組安全掛載區
# ==========================================
try:
    import strategy_core
except ImportError:
    strategy_core = None

try:
    import backtest_engine
except ImportError:
    backtest_engine = None

try:
    import portfolio_monitor
except ImportError:
    portfolio_monitor = None

try:
    import memory_module
except ImportError:
    memory_module = None

try:
    import market_filter
except ImportError:
    market_filter = None

try:
    import yahoo_sniper
except ImportError:
    yahoo_sniper = None

try:
    import broker_memory
except ImportError:
    broker_memory = None

st.set_page_config(
    page_title="HIOS Wave Radar V31",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.sidebar.title("🎯 HIOS Wave Radar")
    st.sidebar.caption("V31 旗艦視覺版")
    
    st.sidebar.header("📂 1. 數據引擎")
    uploaded_csvs = st.sidebar.file_uploader(
        "上傳法人買賣超 CSV (支援多檔歷史資料)", 
        type=['csv'], 
        accept_multiple_files=True
    )
    
    st.sidebar.header("⚙️ 2. 動態濾網設定")
    filter_vol_min = st.sidebar.number_input("💧 5日均量下限 (張)", min_value=0, max_value=20000, value=3000, step=500)
    filter_bias_max = st.sidebar.number_input("🔥 月線乖離率上限 (%)", min_value=1.0, max_value=50.0, value=5.0, step=0.5)
    filter_resonance = st.sidebar.checkbox("🤝 嚴格族群濾網 (共振 >= 3)", value=True)
    
    if memory_module:
        memory_module.render_memory_module()
    else:
        st.sidebar.warning("⚠️ 找不到 `memory_module.py`")

    # ==========================================
    # ⚔️ 旗艦級 UI：戰區 Tabs 重構
    # ==========================================
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🌐 總體風控", 
        "🚀 雷達掃描", 
        "🛡️ 持股監控", 
        "⏳ 時光膠囊",
        "🎯 主力狙擊 (V31)", 
        "🧠 歷史記憶 (V31)"
    ])
    
    with tab1:
        if market_filter:
            market_filter.render_market_dashboard()
        else:
            st.warning("⚠️ 找不到 `market_filter.py`")
            
    with tab2:
        st.header("🚀 雷達掃描室 (雙腦評分系統)")
        if uploaded_csvs and len(uploaded_csvs) > 0:
            st.info(f"📂 已成功載入 {len(uploaded_csvs)} 份 CSV 檔案，準備啟動內部迴圈。")
            if strategy_core:
                try:
                    strategy_core.run_radar(uploaded_csvs, filter_bias_max, filter_resonance, filter_vol_min)
                except Exception as e:
                    st.error(f"雷達運算發生錯誤: {e}")
            else:
                st.warning("⚠️ 找不到 `strategy_core.py`")
        else:
            st.info("👈 請先從左側邊欄上傳「法人買賣超 CSV (可多選)」以啟動雷達。")
            
    with tab3:
        if portfolio_monitor:
            portfolio_monitor.render_portfolio_monitor()
        else:
            st.warning("⚠️ 找不到 `portfolio_monitor.py`")

    with tab4:
        if backtest_engine:
            backtest_engine.render_time_capsule()
        else:
            st.warning("⚠️ 找不到 `backtest_engine.py`")

    # ==========================================
    # 🎯 V31 雙模式狙擊槍 (持股與觀察名單分離版)
    # ==========================================
    with tab5:
        st.header("🎯 V31 主力 X 光狙擊機 (Yahoo 籌碼透視)")
        
        st.subheader("🔫 模式一：單發精準狙擊")
        col1, col2 = st.columns([1, 3])
        with col1:
            target_stock = st.text_input("請輸入股票代號 (例: 5443):", value="5443", key="sniper_input")
            scan_btn = st.button("🚀 啟動單發狙擊", type="primary", use_container_width=True)
            
        if scan_btn and target_stock:
            if yahoo_sniper and broker_memory:
                with st.spinner(f"🕵️‍♂️ 正在潛入 Yahoo 抓取 {target_stock} 今日籌碼..."):
                    sniper = yahoo_sniper.YahooSniper()
                    df_result = sniper.scan_target(target_stock)
                    
                    if df_result is not None and not df_result.empty:
                        st.success(f"✅ 破解成功！已取得 {target_stock} 籌碼明細。")
                        st.dataframe(df_result, use_container_width=True)
                        
                        today_str = datetime.now().strftime("%Y-%m-%d")
                        broker_memory.init_db()
                        broker_memory.save_daily_data(today_str, target_stock, df_result)
                        st.info("💾 戰利品已安全存入本地記憶庫！")
                    else:
                        st.error("❌ 狙擊失敗！目標失去聯繫或防護過強。")
            else:
                st.error("⚠️ 系統警告：找不到 `yahoo_sniper.py` 或 `broker_memory.py`！")

        st.markdown("---")
        
        st.subheader("⚡ 模式二：多目標機槍連發 (持股 + 觀察名單)")
        
        # 🌟 建立代號與名稱的對照表，方便後續顯示
        code_to_name = {}
        portfolio_codes = []
        watchlist_codes = []
        
        # 1. 讀取真實持股 (Portfolio)
        portfolio_list = st.session_state.get('portfolio', [])
        if portfolio_list:
            st.info(f"🛡️ **真實持股區**：已自動載入 {len(portfolio_list)} 檔持股。")
            for item in portfolio_list:
                code = str(item.get('代號', ''))
                code_to_name[code] = item.get('名稱', '')
                portfolio_codes.append(code)
        
        # 2. 讀取雷達結果，建立「觀察名單 (Watchlist)」選擇器
        if 'radar_results' in st.session_state and st.session_state['radar_results']:
            radar_df = pd.DataFrame(st.session_state['radar_results'])
            # 建立選項格式 "代號 - 名稱"
            radar_options = radar_df.apply(lambda x: f"{x['代號']} - {x['名稱']}", axis=1).tolist()
            
            st.markdown("👀 **雷達自選觀察區 (不會混入持股)**：")
            selected_watch = st.multiselect(
                "請從今日雷達名單中，挑選您想「追蹤籌碼」的標的：", 
                radar_options, 
                key="watchlist_select"
            )
            
            # 存入 session_state 供 Tab 6 使用
            st.session_state['watchlist'] = selected_watch
            
            for sw in selected_watch:
                code = sw.split(" - ")[0]
                name = sw.split(" - ")[1]
                code_to_name[code] = name
                watchlist_codes.append(code)
                
        # 3. 合併所有要狙擊的目標 (去重複)
        target_codes = list(set(portfolio_codes + watchlist_codes))
        
        if target_codes:
            st.write("")
            if st.button(f"🔥 一鍵自動狙擊這 {len(target_codes)} 檔標的，並存入記憶庫", type="primary", use_container_width=True):
                if yahoo_sniper and broker_memory:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    broker_memory.init_db()
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    
                    success_count = 0
                    fail_list = []
                    
                    for i, code in enumerate(target_codes):
                        name = code_to_name.get(code, '')
                        status_text.text(f"🕵️‍♂️ 正在狙擊第 {i+1}/{len(target_codes)} 檔：{code} {name} ...")
                        
                        sniper = yahoo_sniper.YahooSniper()
                        df_result = sniper.scan_target(code)
                        
                        if df_result is not None and not df_result.empty:
                            try:
                                broker_memory.save_daily_data(today_str, code, df_result)
                                success_count += 1
                            except Exception as e:
                                fail_list.append(f"{code} (資料庫寫入失敗)")
                        else:
                            fail_list.append(f"{code} (Yahoo 抓取失敗)")
                            
                        progress_bar.progress((i + 1) / len(target_codes))
                        time.sleep(random.uniform(1.5, 3.5)) 
                        
                    status_text.empty()
                    
                    if success_count == len(target_codes):
                        st.success(f"✅ 狙擊任務大獲全勝！成功將 {success_count} 檔標的籌碼存入記憶庫。")
                    else:
                        st.warning(f"⚠️ 狙擊任務結束。成功：{success_count} 檔，失敗：{len(fail_list)} 檔。")
                        if fail_list:
                            st.error(f"❌ 失敗名單：{', '.join(fail_list)}")
                else:
                    st.error("⚠️ 系統警告：找不到 `yahoo_sniper.py` 或 `broker_memory.py`！")
        else:
            st.warning("⚠️ 目前沒有鎖定任何目標。請先加入持股，或從上方雷達名單中挑選觀察標的！")

    # ==========================================
    # 🧠 V31 歷史記憶庫 (雙軌合併下拉選單)
    # ==========================================
    with tab6:
        st.header("🧠 歷史記憶庫 (多日籌碼加總)")
        st.markdown("調閱本地資料庫，自動加總過去 N 天的主力買賣超，讓**隔日沖**與**波段鎖碼主力**無所遁形！")
        
        col_m1, col_m2 = st.columns([1, 3])
        with col_m1:
            # 🌟 雙軌合併：將持股與觀察名單合併為下拉選單
            portfolio_list = st.session_state.get('portfolio', [])
            p_options = [f"{item.get('代號', '')} - {item.get('名稱', '')}" for item in portfolio_list]
            w_options = st.session_state.get('watchlist', [])
            
            all_options = list(set(p_options + w_options))
            all_options.sort() # 依代號排序
            
            if all_options:
                selected_option = st.selectbox("🎯 選擇要查詢的標的 (含持股與觀察名單):", all_options, key="query_stock_select")
                query_stock = selected_option.split(" - ")[0]
            else:
                query_stock = st.text_input("查詢股票代號:", value="5443", key="query_stock_input")
                st.caption("💡 提示：在 Tab 5 挑選觀察名單後，這裡會自動變成下拉選單！")
                
            query_days = st.slider("查詢天數:", min_value=1, max_value=20, value=5)
            query_btn = st.button("🔍 調閱歷史記憶", type="primary", use_container_width=True)
            
        if query_btn:
            if broker_memory:
                with st.spinner("正在計算歷史籌碼..."):
                    broker_memory.init_db()
                    df_history = broker_memory.get_multi_day_concentration(query_stock, days=query_days)
                    
                    if df_history is not None and not df_history.empty:
                        st.success(f"🎯 成功調閱 {query_stock} 歷史記憶！以下為區間前 15 大主力：")
                        st.dataframe(df_history, use_container_width=True)
                    else:
                        st.warning(f"⚠️ 記憶庫中目前沒有 {query_stock} 的歷史資料。請確認代號是否正確，或先執行狙擊任務！")
            else:
                st.error("⚠️ 系統警告：找不到 `broker_memory.py`，無法調閱記憶庫！")

if __name__ == "__main__":
    main()
