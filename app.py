import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import io

# ==========================================
# 1. 系統初始化與 UI 設定
# ==========================================
st.set_page_config(page_title="HIOS Wave Radar V18.3", layout="wide")
st.title("🌊 HIOS Wave Radar V18.3 - 機構級量化雷達")
st.markdown("### 雙核心引擎：低乖離防守 × 投信動能攻擊 (漏斗篩選架構)")

# ==========================================
# 2. 側邊欄：參數設定與資料匯入
# ==========================================
st.sidebar.header("⚙️ 戰術參數設定")

strategy = st.sidebar.radio("選擇策略", ["A策略 (低乖離防守)", "B策略 (季線突破動能)"])

st.sidebar.markdown("---")
st.sidebar.subheader("🕒 掃描模式切換")
is_intraday = st.sidebar.checkbox("⚡ 啟用盤中狙擊模式", value=False, 
                                  help="盤中勾選此項，將自動關閉「周轉率」與「溫和放量」濾網，避免盤中資料失真導致誤殺。")

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ 絕對濾網 (Hard Filters)")
min_trust_buy = st.sidebar.number_input("投信買超下限 (張)", value=100, step=50)
max_bias = st.sidebar.number_input("MA20 乖離率上限 (%)", value=5.0, step=0.5)
max_turnover = st.sidebar.number_input("周轉率上限 (%)", value=10.0, step=1.0, help="排除當沖妖股 (盤中模式將忽略此項)")
vol_expansion = st.sidebar.number_input("溫和放量倍數 (今日/5日均量)", value=1.2, step=0.1, help="確保有大人點火 (盤中模式將忽略此項)")

st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader("上傳三大法人 CSV (請確保為最新交易日)", type="csv")

# ==========================================
# 3. 核心運算函數
# ==========================================
@st.cache_data(ttl=300)
def fetch_and_calculate(df_chips):
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
            volume = latest['Volume'] / 1000
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

def v18_funnel_filter_and_score(df, intraday_mode):
    filtered_df = df.copy()
    
    # --- 第一階段：絕對鐵門 ---
    filtered_df = filtered_df[(filtered_df['投信買賣超'] >= min_trust_buy) & (filtered_df['外資買賣超'] > -1000)]
    filtered_df = filtered_df[filtered_df['收盤價'] > filtered_df['MA60']]
    filtered_df = filtered_df[filtered_df['MA20_乖離率'] <= max_bias]
    
    if not intraday_mode:
        if '周轉率' in filtered_df.columns and (filtered_df['周轉率'] > 0).any():
            filtered_df = filtered_df[filtered_df['周轉率'] <= max_turnover]
        filtered_df = filtered_df[filtered_df['成交量'] >= (filtered_df['5日均量'] * vol_expansion)]
    
    # --- 第二階段：優選評分 ---
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
# 4. 主程式執行區 (終極防彈讀取法)
# ==========================================
if uploaded_file is not None:
    try:
        # 1. 將檔案讀取為原始位元組
        raw_bytes = uploaded_file.read()
        decoded_text = None
        
        # 2. 嚴格測試編碼 (不允許亂碼產生)
        for enc in ['utf-8-sig', 'utf-8', 'cp950', 'big5']:
            try:
                decoded_text = raw_bytes.decode(enc)
                break # 成功解碼就跳出
            except UnicodeDecodeError:
                continue
                
        # 如果真的都失敗，才用強制略過
        if decoded_text is None:
            decoded_text = raw_bytes.decode('cp950', errors='ignore')
            
        # 3. 尋找真正的標題行
        lines = decoded_text.splitlines()
        skip_rows = 0
        for i, line in enumerate(lines):
            clean_line = line.replace(' ', '').replace('"', '')
            if '代號' in clean_line:
                skip_rows = i
                break
                
        # 4. 使用 io.StringIO 將純文字轉回 CSV 給 Pandas 讀取
        df_raw = pd.read_csv(io.StringIO(decoded_text), skiprows=skip_rows)
        
        # 5. 欄位自動校正與清洗
        df_raw.columns = df_raw.columns.str.strip()
        col_mapping = {
            '證券代號': '代號', '股票代號': '代號',
            '證券名稱': '名稱', '股票名稱': '名稱',
            '投信買賣超股數': '投信買賣超', '外資買賣超股數': '外資買賣超'
        }
        df_raw = df_raw.rename(columns=col_mapping)
        
        # 6. 數字欄位防呆 (清除千分位逗號)
        for col in ['投信買賣超', '外資買賣超', '周轉率']:
            if col in df_raw.columns:
                if df_raw[col].dtype == object:
                    df_raw[col] = pd.to_numeric(df_raw[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        
        if '代號' not in df_raw.columns:
            st.error(f"⚠️ 找不到「代號」欄位！目前 CSV 擁有的欄位為：{list(df_raw.columns)}")
        else:
            st.success(f"✅ 成功匯入籌碼資料，共 {len(df_raw)} 筆標的。")
            
            if st.button("🚀 啟動 V18.3 漏斗掃描"):
                with st.spinner("正在聯網獲取即時報價與計算指標..."):
                    df_analyzed = fetch_and_calculate(df_raw)
                    df_final = v18_funnel_filter_and_score(df_analyzed, is_intraday)
                    
                    if not df_final.empty:
                        st.balloons()
                        mode_text = "盤中狙擊模式 (已放寬量能濾網)" if is_intraday else "盤後嚴格模式 (全鐵門啟動)"
                        st.markdown(f"### 🎯 掃描完成！[{mode_text}] 共篩選出 {len(df_final)} 檔 S 級真龍")
                        st.dataframe(df_final.style.background_gradient(subset=['綜合評分'], cmap='YlOrRd'))
                    else:
                        st.warning("⚠️ 在目前的嚴格濾網下，沒有股票符合條件。這代表目前盤勢可能不佳，建議保留現金！")
                        
    except Exception as e:
        st.error(f"檔案讀取發生未預期錯誤: {e}")
else:
    st.info("請先從左側上傳今日最新的「三大法人.csv」檔案。")
