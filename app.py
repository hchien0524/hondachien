import streamlit as st
import pandas as pd
import json
import time
import random
import os
import zipfile
import io
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

# ==========================================
# 💾 本機/雲端暫存記憶晶片
# ==========================================
DATA_FILE = "hios_data.json"
DB_FILE = "broker_memory.db"

def load_local_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({"portfolio": [], "watchlist": []}, f, ensure_ascii=False, indent=4)
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_local_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def create_backup_zip():
    """將 JSON 和 DB 打包成 ZIP 供下載"""
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(DATA_FILE):
            zf.write(DATA_FILE)
        if os.path.exists(DB_FILE):
            zf.write(DB_FILE)
    memory_file.seek(0)
    return memory_file

def main():
    # 🌟 啟動時自動同步資料與網頁暫存
    local_data = load_local_data()
    
    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = local_data.get('portfolio', [])
    elif st.session_state['portfolio'] != local_data.get('portfolio', []):
        local_data['portfolio'] = st.session_state['portfolio']
        save_local_data(local_data)
        
    if 'watchlist' not in st.session_state:
        st.session_state['watchlist'] = local_data.get('watchlist', [])
    elif st.session_state['watchlist'] != local_data.get('watchlist', []):
        local_data['watchlist'] = st.session_state['watchlist']
        save_local_data(local_data)

    st.sidebar.title("🎯 HIOS Wave Radar")
    st.sidebar.caption("V31 旗艦視覺版 (手動存檔防護)")
    
    # ==========================================
    # 💾 側邊欄：系統記憶存檔與還原 (V31 核心升級)
    # ==========================================
    st.sidebar.header("💾 0. 記憶存檔與還原")
    st.sidebar.markdown("雲端防護機制：每日請手動備份與還原")
    
    # 讀檔還原區
    uploaded_backup = st.sidebar.file_uploader("📥 1. 上班讀檔：上傳 HIOS_Backup.zip", type=['zip'])
    if uploaded_backup is not None:
        if st.sidebar.button("🔄 執行記憶還原", type="primary", use_container_width=True):
            try:
                with zipfile.ZipFile(uploaded_backup, 'r') as zf:
                    zf.extractall() # 解壓縮並覆蓋現有檔案
                st.sidebar.success("✅ 記憶還原成功！系統已滿血復活。")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"還原失敗: {e}")
                
    # 存檔下載區
    st.sidebar.markdown("---")
    st.sidebar.markdown("📤 **2. 下班存檔：下載最新記憶**")
    backup_zip = create_backup_zip()
    today_str = datetime.now().strftime("%Y%m%d")
    st.sidebar.download_button(
        label="💾 下載今日系統備份檔 (.zip)",
        data=backup_zip,
        file_name=f"HIOS_Backup_{today_str}.zip",
        mime="application/zip",
        use_container_width=True
    )
    st.sidebar.markdown("---")

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
    # 🎯 V31 雙模式狙擊槍
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
                        st.info("💾 戰利品已安全存入本地記憶庫！請記得在左側邊欄下載備份！")
                    else:
                        st.error("❌ 狙擊失敗！目標失去聯繫或防護過強。")
            else:
                st.error("⚠️ 系統警告：找不到 `yahoo_sniper.py` 或 `broker_memory.py`！")

        st.markdown("---")
        
        st.subheader("👀 觀察名單管理")
        current_watchlist = st.session_state.get('watchlist', [])
        if current_watchlist:
            st.write(f"**目前觀察名單：** {', '.join([f'{w.get('代號','')} {w.get('名稱','')}' for w in current_watchlist])}")
            if st.button("🗑️ 清空觀察名單"):
                st.session_state['watchlist'] = []
                save_local_data({"portfolio": st.session_state.get('portfolio', []), "watchlist": []})
                st.rerun()
        else:
            st.write("目前觀察名單為空。")

        if 'radar_results' in st.session_state and st.session_state['radar_results']:
            if st.button("⚡ 一鍵將今日雷達前 10 名寫入觀察名單", type="secondary"):
                top_10 = sorted(st.session_state['radar_results'], key=lambda x: x['🔥 總分'], reverse=True)[:10]
                existing_codes = [w.get('代號', '') for w in st.session_state.get('watchlist', [])]
                added = 0
                for r in top_10:
                    if r['代號'] not in existing_codes:
                        st.session_state['watchlist'].append({"代號": r['代號'], "名稱": r['名稱']})
                        added += 1
                if added > 0:
                    save_local_data({"portfolio": st.session_state.get('portfolio', []), "watchlist": st.session_state['watchlist']})
                    st.success(f"✅ 成功寫入！請記得在左側邊欄下載備份！")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.info("雷達前 10 名皆已在觀察名單中。")

        st.markdown("---")
        
        st.subheader("⚡ 模式二：多目標機槍連發 (持股 + 觀察名單)")
        target_list = []
        seen_codes = set()
        
        for item in st.session_state.get('portfolio', []):
            code = str(item.get('代號', ''))
            if code and code not in seen_codes:
                target_list.append(item)
                seen_codes.add(code)
                
        for item in st.session_state.get('watchlist', []):
            code = str(item.get('代號', ''))
            if code and code not in seen_codes:
                target_list.append(item)
                seen_codes.add(code)
                
        if target_list:
            st.info(f"🛡️ 系統已載入 {len(target_list)} 檔標的 (含持股與觀察名單)。")
            cols = st.columns(5)
            for i, item in enumerate(target_list):
                stock_code = item.get('代號', '')
                stock_name = item.get('名稱', '')
                cols[i % 5].info(f"**{stock_code}**\n\n{stock_name}")
            
            st.write("")
            if st.button(f"🔥 一鍵自動狙擊這 {len(target_list)} 檔標的，並存入記憶庫", type="primary", use_container_width=True):
                if yahoo_sniper and broker_memory:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    broker_memory.init_db()
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    
                    success_count = 0
                    fail_list = []
                    
                    for i, item in enumerate(target_list):
                        code = str(item.get('代號', ''))
                        name = item.get('名稱', '')
                        status_text.text(f"🕵️‍♂️ 正在狙擊第 {i+1}/{len(target_list)} 檔：{code} {name} ...")
                        
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
                            
                        progress_bar.progress((i + 1) / len(target_list))
                        time.sleep(random.uniform(1.5, 3.5)) 
                        
                    status_text.empty()
                    
                    if success_count == len(target_list):
                        st.success(f"✅ 狙擊任務大獲全勝！請務必到左側邊欄點擊「下載今日系統備份檔」！")
                    else:
                        st.warning(f"⚠️ 狙擊任務結束。成功：{success_count} 檔，失敗：{len(fail_list)} 檔。")
                        if fail_list:
                            st.error(f"❌ 失敗名單：{', '.join(fail_list)}")
                else:
                    st.error("⚠️ 系統警告：找不到 `yahoo_sniper.py` 或 `broker_memory.py`！")
        else:
            st.warning("⚠️ 目前沒有任何持股或觀察名單。")

    # ==========================================
    # 🧠 V31 歷史記憶庫
    # ==========================================
    with tab6:
        st.header("🧠 歷史記憶庫 (多日籌碼加總)")
        st.markdown("調閱本地資料庫，自動加總過去 N 天的主力買賣超，讓**隔日沖**與**波段鎖碼主力**無所遁形！")
        
        col_m1, col_m2 = st.columns([1, 3])
        with col_m1:
            p_list = st.session_state.get('portfolio', [])
            w_list = st.session_state.get('watchlist', [])
            
            p_options = [f"{item.get('代號', '')} - {item.get('名稱', '')}" for item in p_list if item.get('代號')]
            w_options = [f"{item.get('代號', '')} - {item.get('名稱', '')}" for item in w_list if item.get('代號')]
            
            all_options = list(set(p_options + w_options))
            all_options.sort()
            
            if all_options:
                selected_option = st.selectbox("🎯 選擇要查詢的標的:", all_options, key="query_stock_select")
                query_stock = selected_option.split(" - ")[0]
            else:
                query_stock = st.text_input("查詢股票代號:", value="5443", key="query_stock_input")
                
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
                        st.warning(f"⚠️ 記憶庫中目前沒有 {query_stock} 的歷史資料。請確認是否已上傳備份檔，或先執行狙擊任務！")
            else:
                st.error("⚠️ 系統警告：找不到 `broker_memory.py`，無法調閱記憶庫！")

if __name__ == "__main__":
    main()
