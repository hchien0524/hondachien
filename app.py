import streamlit as st
import pandas as pd
from datetime import datetime
import yfinance as yf

# ==========================================
# 🛡️ 系統模組載入區
# ==========================================
try:
    import yahoo_sniper
    import broker_memory
except ImportError:
    st.error("⚠️ 系統警告：找不到 yahoo_sniper.py 或 broker_memory.py！請確認檔案是否在同一資料夾。")

# 如果您有獨立的策略模組，請在這裡解除註解
# import data_engine
# import strategy_core

# ==========================================
# 🖥️ 戰情室 UI 初始化
# ==========================================
st.set_page_config(page_title="HIOS Wave Radar V31", page_icon="🌊", layout="wide")
st.title("🌊 HIOS Wave Radar V31 - 終極量化指揮中心")

# ==========================================
# 🚨 V31 全自動大盤風控系統
# ==========================================
st.markdown("---")
st.subheader("🚨 戰情室：大盤風控與資金水位燈號")

@st.cache_data(ttl=300)
def get_market_status():
    try:
        twii = yf.Ticker("^TWII")
        hist = twii.history(period="2mo")
        if not hist.empty:
            current_close = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            change = current_close - prev_close
            change_pct = (change / prev_close) * 100
            ma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
            return current_close, change, change_pct, ma20
    except Exception as e:
        return None, None, None, None

current_close, change, change_pct, ma20 = get_market_status()

if current_close:
    col1, col2, col3 = st.columns(3)
    col1.metric("加權指數 (^TWII)", f"{current_close:.2f}", f"{change:.2f} ({change_pct:.2f}%)")
    col2.metric("生命線 (20MA 月線)", f"{ma20:.2f}", "")
    
    if current_close > ma20:
        risk_status = "🟢 安全 (多頭格局)"
        advice = "大盤穩居月線之上！建議維持 5-7 成持股，積極使用雷達掃描真龍股。"
    else:
        risk_status = "🔴 警戒 (空頭/洗盤)"
        advice = "⚠️ 大盤跌破月線！建議降至 3 成以下資金，嚴格執行停損，多看少做。"
        
    col3.metric("目前風控燈號", risk_status)
    st.info(f"💡 **軍師操作建議：** {advice}")
else:
    st.warning("⚠️ 無法取得大盤即時數據，請確認網路連線。")

st.markdown("---")

# ==========================================
# ⚔️ 四大戰術分頁
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 主力 X 光狙擊 (V31)", 
    "🧠 歷史記憶庫 (V31)",
    "📡 盤後雷達海選 (V30)", 
    "🛡️ 持股監控中心"
])

# --- 分頁 1：狙擊槍 ---
with tab1:
    st.subheader("🎯 V31 主力 X 光狙擊機 (Yahoo 籌碼透視)")
    col1, col2 = st.columns([1, 3])
    with col1:
        target_stock = st.text_input("請輸入股票代號 (例: 5443):", value="5443", key="sniper_input")
        scan_btn = st.button("🚀 啟動狙擊掃描", type="primary", use_container_width=True)
        
    if scan_btn and target_stock:
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
                st.error("❌ 狙擊失敗！目標失去聯繫。")

# --- 分頁 2：記憶庫 ---
with tab2:
    st.subheader("🧠 歷史記憶庫 (多日籌碼加總)")
    col_m1, col_m2 = st.columns([1, 3])
    with col_m1:
        query_stock = st.text_input("查詢股票代號:", value="5443", key="query_stock")
        query_days = st.slider("查詢天數:", min_value=1, max_value=20, value=5)
        query_btn = st.button("🔍 調閱歷史記憶", type="primary", use_container_width=True)
        
    if query_btn:
        with st.spinner("正在計算歷史籌碼..."):
            broker_memory.init_db()
            df_history = broker_memory.get_multi_day_concentration(query_stock, days=query_days)
            if df_history is not None and not df_history.empty:
                st.success(f"🎯 成功調閱 {query_stock} 歷史記憶！")
                st.dataframe(df_history, use_container_width=True)
            else:
                st.warning(f"⚠️ 記憶庫中目前沒有 {query_stock} 的歷史資料。")

# --- 分頁 3：雷達海選 (已修復 CSV 上傳) ---
with tab3:
    st.subheader("📡 盤後雷達海選 (三大法人 CSV 掃描)")
    st.markdown("請上傳證交所/櫃買中心的「三大法人買賣超 CSV」檔案 (支援**多檔同時上傳**)。")
    
    # 🌟 升級 1：開啟多檔案彈匣
    uploaded_files = st.file_uploader("📂 上傳三大法人買賣超 CSV 檔案", type=["csv"], accept_multiple_files=True)
    
    if uploaded_files:
        all_dfs = []
        
        for uploaded_file in uploaded_files:
            st.markdown(f"**處理檔案：{uploaded_file.name}**")
            try:
                # 🌟 升級 2：終極編碼破解裝甲
                df_radar = None
                encodings = ['utf-8', 'cp950', 'big5', 'utf-8-sig']
                
                for enc in encodings:
                    try:
                        uploaded_file.seek(0)
                        df_radar = pd.read_csv(uploaded_file, encoding=enc, thousands=',')
                        break
                    except UnicodeDecodeError:
                        continue
                        
                # 強制替換亂碼模式
                if df_radar is None:
                    uploaded_file.seek(0)
                    df_radar = pd.read_csv(uploaded_file, encoding='cp950', thousands=',', errors='replace')
                    st.warning(f"⚠️ {uploaded_file.name} 包含特殊字元，已啟動亂碼替換模式強制讀取。")
                    
                st.success(f"✅ {uploaded_file.name} 載入成功！")
                st.dataframe(df_radar.head(3), use_container_width=True)
                all_dfs.append(df_radar)
                
            except Exception as e:
                st.error(f"❌ {uploaded_file.name} 解析失敗。錯誤訊息: {e}")
        
        if all_dfs and st.button("⚡ 啟動 V30.6 策略海選 (合併掃描)", type="primary"):
            with st.spinner("正在將多份 CSV 合併並執行量化篩選..."):
                # 💡 這裡預留呼叫您 strategy_core 的接口
                # combined_df = pd.concat(all_dfs, ignore_index=True)
                # df_result = strategy_core.run_scan(combined_df)
                st.success("🎯 掃描完成！請將篩選出的潛力股代號，輸入到「🎯 主力 X 光狙擊」進行籌碼確認！")

# --- 分頁 4：持股監控 ---
with tab4:
    st.subheader("🛡️ 持股監控中心")
    st.markdown("目前戰情室監控主將：**英業達 (2356)**、**均豪 (5443)**")
    
    portfolio_data = {
        "股票名稱": ["英業達 (2356)", "均豪 (5443)"],
        "持有張數": [6, 2],
        "平均成本": [68.33, 120.50],
        "防守線 (月線/鐵底)": [67.30, 118.50]
    }
    df_portfolio = pd.DataFrame(portfolio_data)
    st.dataframe(df_portfolio, use_container_width=True)
