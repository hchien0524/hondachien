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

# --- 分頁 3：雷達海選 (內建極速濾波器) ---
with tab3:
    st.subheader("📡 盤後雷達海選 (三大法人 CSV 掃描)")
    st.markdown("請上傳證交所/櫃買中心的「三大法人買賣超 CSV」檔案 (支援**多檔同時上傳**)。")
    
    uploaded_files = st.file_uploader("📂 上傳三大法人買賣超 CSV 檔案", type=["csv"], accept_multiple_files=True)
    
    if uploaded_files:
        all_dfs = []
        for uploaded_file in uploaded_files:
            try:
                df_radar = None
                encodings = ['utf-8', 'cp950', 'big5', 'utf-8-sig']
                for enc in encodings:
                    try:
                        uploaded_file.seek(0)
                        df_radar = pd.read_csv(uploaded_file, encoding=enc, thousands=',')
                        break
                    except UnicodeDecodeError:
                        continue
                        
                if df_radar is None:
                    uploaded_file.seek(0)
                    df_radar = pd.read_csv(uploaded_file, encoding='cp950', thousands=',', errors='replace')
                    
                all_dfs.append(df_radar)
                st.success(f"✅ {uploaded_file.name} 載入成功！")
            except Exception as e:
                st.error(f"❌ {uploaded_file.name} 解析失敗。錯誤訊息: {e}")
        
        if all_dfs and st.button("⚡ 啟動 V31 內建真龍海選", type="primary"):
            with st.spinner("正在合併資料並無情斬殺 ETF 與權證..."):
                try:
                    # 1. 合併所有 CSV
                    combined_df = pd.concat(all_dfs, ignore_index=True)
                    
                    # 2. 清洗欄位名稱 (去除空白)
                    combined_df.columns = combined_df.columns.str.strip()
                    
                    # 3. 自動尋找關鍵欄位
                    code_col = next((c for c in combined_df.columns if '代號' in c), None)
                    name_col = next((c for c in combined_df.columns if '名稱' in c), None)
                    net_buy_col = next((c for c in combined_df.columns if '三大法人買賣超' in c or '買賣超' in c), None)
                    
                    if code_col and name_col:
                        # 將代號轉為字串並去除空白
                        combined_df[code_col] = combined_df[code_col].astype(str).str.strip()
                        
                        # 🛡️ 核心濾波邏輯：剔除 0 開頭(ETF) 與 7 開頭(權證)
                        mask = ~combined_df[code_col].str.startswith(('0', '7'))
                        filtered_df = combined_df[mask].copy()
                        
                        # 如果有買賣超欄位，進行數值轉換與排序
                        if net_buy_col:
                            filtered_df[net_buy_col] = pd.to_numeric(filtered_df[net_buy_col].astype(str).str.replace(',', ''), errors='coerce')
                            filtered_df = filtered_df.sort_values(by=net_buy_col, ascending=False)
                        
                        st.success("🎯 掃描完成！已成功剔除 ETF 與權證，以下為今日法人買超主力股 (前 50 名)：")
                        
                        # 重新整理欄位順序，讓代號、名稱、買賣超排在最前面
                        cols = filtered_df.columns.tolist()
                        important_cols = [code_col, name_col]
                        if net_buy_col: important_cols.append(net_buy_col)
                        other_cols = [c for c in cols if c not in important_cols]
                        filtered_df = filtered_df[important_cols + other_cols]
                        
                        st.dataframe(filtered_df.head(50), use_container_width=True)
                    else:
                        st.warning("⚠️ 無法自動識別「代號」或「買賣超」欄位，顯示原始合併資料：")
                        st.dataframe(combined_df, use_container_width=True)
                        
                except Exception as e:
                    st.error(f"❌ 篩選過程發生錯誤：{e}")

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
