import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta

# ==========================================
# 1. 系統初始化與 UI 設定
# ==========================================
st.set_page_config(page_title="HIOS Wave Radar V18.0", layout="wide")
st.title("🌊 HIOS Wave Radar V18.0 - 機構級量化雷達")
st.markdown("### 雙核心引擎：低乖離防守 × 投信動能攻擊 (漏斗篩選架構)")

# ==========================================
# 2. 側邊欄：參數設定與資料匯入
# ==========================================
st.sidebar.header("⚙️ 戰術參數設定")

# 策略選擇
strategy = st.sidebar.radio("選擇策略", ["A策略 (低乖離防守)", "B策略 (季線突破動能)"])

# V18 新增：漏斗篩選參數
st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ 絕對濾網 (Hard Filters)")
min_trust_buy = st.sidebar.number_input("投信買超下限 (張)", value=100, step=50)
max_bias = st.sidebar.number_input("MA20 乖離率上限 (%)", value=5.0, step=0.5)
max_turnover = st.sidebar.number_input("周轉率上限 (%)", value=10.0, step=1.0, help="排除當沖妖股")
vol_expansion = st.sidebar.number_input("溫和放量倍數 (今日/5日均量)", value=1.2, step=0.1, help="確保有大人點火")

st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader("上傳三大法人 CSV (請確保為最新交易日)", type="csv")

# ==========================================
# 3. 核心運算函數
# ==========================================
@st.cache_data(ttl=300) # 快取 5 分鐘
def fetch_and_calculate(df_chips):
    """抓取 yfinance 即時報價並計算技術指標"""
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_stocks = len(df_chips)
    
    for i, row in df_chips.iterrows():
        stock_code = str(row['代號']).strip()
        yf_code = f"{stock_code}.TW" 
        
        try:
            hist = yf.Ticker(yf_code).history(period="3mo")
            if len(hist) < 60:
                continue
                
            hist['MA20'] = hist['Close'].rolling(window=20).mean()
            hist['MA60'] = hist['Close'].rolling(window=60).mean()
            hist['MA5_Vol'] = hist['Volume'].rolling(window=5).mean()
            
            latest = hist.iloc[-1]
            close_price = latest['Close']
            ma20 = latest['MA20']
            ma60 = latest['MA60']
            volume = latest['Volume'] / 1000 # 轉換為張數
            ma5_vol = latest['MA5_Vol'] / 1000
            
            bias_20 = ((close_price - ma20) / ma20) * 100
            
            stock_data = {
                '代號': stock_code,
                '名稱': row.get('名稱', '未知'),
                '收盤價': round(close_price, 2),
                'MA20_乖離率': round(bias_20, 2),
                'MA60': round(ma60, 2),
                '成交量': round(volume, 0),
                '5日均量': round(ma5_vol, 0),
                '投信買賣超': row.get('投信買賣超', 0),
                '外資買賣超': row.get('外資買賣超', 0),
                '周轉率': row.get('周轉率', 0)
            }
            results.append(stock_data)
            
        except Exception:
            pass
            
        progress_bar.progress((i + 1) / total_stocks)
        status_text.text(f"正在掃描: {stock_code} ({i+1}/{total_stocks})")
        
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results)

def v18_funnel_filter_and_score(df):
    """V18 機構級漏斗篩選與評分"""
    filtered_df = df.copy()
    
    # --- 第一階段：絕對鐵門 (Hard Filters) ---
    filtered_df = filtered_df[(filtered_df['投信買賣超'] >= min_trust_buy) & (filtered_df['外資買賣超'] > -1000)]
    filtered_df = filtered_df[filtered_df['收盤價'] > filtered_df['MA60']]
    filtered_df = filtered_df[filtered_df['MA20_乖離率'] <= max_bias]
    
    if (filtered_df['周轉率'] > 0).any():
        filtered_df = filtered_df[filtered_df['周轉率'] <= max_turnover]
        
    filtered_df = filtered_df[filtered_df['成交量'] >= (filtered_df['5日均量'] * vol_expansion)]
    
    # --- 第二階段：優選評分 (Scoring) ---
    if filtered_df.empty:
        return filtered_df
        
    t_min, t_max = filtered_df['投信買賣超'].min(), filtered_df['投信買賣超'].max()
    if t_max > t_min:
        filtered_df['投信分數'] = (filtered_df['投信買賣超'] - t_min) / (t_max - t_min) * 60
    else:
        filtered_df['投信分數'] = 60
        
    b_min, b_max = filtered_df['MA20_乖離率'].min(), filtered_df['MA20_乖離率'].max()
    if b_max > b_min:
        filtered_df['乖離分數'] = (b_max - filtered_df['MA20_乖離率']) / (b_max - b_min) * 40
    else:
        filtered_df['乖離分數'] = 40
        
    filtered_df['綜合評分'] = np.round(filtered_df['投信分數'] + filtered_df['乖離分數'], 0)
    filtered_df = filtered_df.sort_values(by='綜合評分', ascending=False).reset_index(drop=True)
    
    def get_stars(score):
        if score >= 90: return '🌟🌟🌟🌟🌟'
        elif score >= 80: return '🌟🌟🌟🌟'
        elif score >= 70: return '🌟🌟🌟'
        else: return '🌟🌟'
        
    filtered_df['推薦星等'] = filtered_df['綜合評分'].apply(get_stars)
    
    display_cols = ['代號', '名稱', '收盤價', '綜合評分', '推薦星等', 'MA20_乖離率', '投信買賣超', '外資買賣超', '成交量', '5日均量']
    return filtered_df[display_cols]

# ==========================================
# 4. 主程式執行區 (包含終極防呆讀取)
# ==========================================
if uploaded_file is not None:
    try:
        encodings_to_try = ['utf-8', 'cp950', 'big5', 'utf-8-sig']
        df_raw = None
        
        for enc in encodings_to_try:
            try:
                uploaded_file.seek(0)
                df_raw = pd.read_csv(uploaded_file, encoding=enc, encoding_errors='ignore')
                break
            except Exception:
                continue
                
        if df_raw is not None and not df_raw.empty:
            st.success(f"✅ 成功匯入籌碼資料，共 {len(df_raw)} 筆標的。")
            
            if st.button("🚀 啟動 V18 漏斗掃描"):
                with st.spinner("正在聯網獲取即時報價與計算指標..."):
                    df_analyzed = fetch_and_calculate(df_raw)
                    df_final = v18_funnel_filter_and_score(df_analyzed)
                    
                    if not df_final.empty:
                        st.balloons()
                        st.markdown(f"### 🎯 掃描完成！共篩選出 {len(df_final)} 檔 S 級真龍")
                        st.dataframe(df_final.style.background_gradient(subset=['綜合評分'], cmap='YlOrRd'))
                    else:
                        st.warning("⚠️ 在目前的嚴格濾網下，沒有股票符合條件。這代表目前盤勢可能不佳，建議保留現金！")
        else:
            st.error("⚠️ 無法解析檔案編碼，請確認 CSV 格式是否正確。")
            
    except Exception as e:
        st.error(f"檔案讀取發生未預期錯誤: {e}")
else:
    st.info("請先從左側上傳今日最新的「三大法人.csv」檔案。")
