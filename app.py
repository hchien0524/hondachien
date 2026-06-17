import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import io
import requests
import re

# ==========================================
# 模組一：系統初始化與 UI 框架
# ==========================================
st.set_page_config(page_title="HIOS Wave Radar V19.6", layout="wide")
st.title("🌊 HIOS Wave Radar V19.6 - 上帝視角版")
st.markdown("### 終極量化核心：全市場直連 × 終極正則清洗 × 戰情室除錯")

# ==========================================
# 模組二：全市場名單獲取
# ==========================================
@st.cache_data(ttl=86400)
def fetch_tw_universe():
    stocks = []
    try:
        res_twse = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", timeout=5 )
        if res_twse.status_code == 200:
            for item in res_twse.json():
                if len(str(item.get('Code', ''))) == 4:
                    stocks.append({'代號': str(item['Code']), '名稱': str(item['Name']), '市場': '上市'})
    except: pass
    try:
        res_tpex = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes", timeout=5 )
        if res_tpex.status_code == 200:
            for item in res_tpex.json():
                if len(str(item.get('SecuritiesCompanyCode', ''))) == 4:
                    stocks.append({'代號': str(item['SecuritiesCompanyCode']), '名稱': str(item['CompanyName']), '市場': '上櫃'})
    except: pass
    df_universe = pd.DataFrame(stocks)
    if df_universe.empty: return pd.DataFrame(columns=['代號', '名稱', '市場'])
    return df_universe.drop_duplicates(subset=['代號'])

# ==========================================
# 模組三：終極正則清洗與數據提取
# ==========================================
def clean_number(val):
    if pd.isna(val): return 0
    val_str = str(val).strip()
    if val_str.startswith('(') and val_str.endswith(')'):
        val_str = '-' + val_str[1:-1]
    val_str = re.sub(r'[^\d\.-]', '', val_str)
    try: return float(val_str) if val_str else 0
    except: return 0

def parse_chip_csv(uploaded_file):
    raw_bytes = uploaded_file.read()
    decoded_text = None
    for enc in ['utf-8-sig', 'utf-8', 'cp950', 'big5']:
        try:
            decoded_text = raw_bytes.decode(enc)
            break
        except UnicodeDecodeError: continue
    if not decoded_text: decoded_text = raw_bytes.decode('cp950', errors='ignore')
        
    lines = decoded_text.splitlines()
    skip_rows = 0
    for i, line in enumerate(lines):
        if '代號' in line.replace(' ', '').replace('"', ''):
            skip_rows = i
            break
            
    df = pd.read_csv(io.StringIO(decoded_text), skiprows=skip_rows)
    
    trust_col, foreign_col, code_col, name_col, turn_col = None, None, None, None, None
    for c in df.columns:
        c_str = str(c).replace(' ', '').replace('"', '').replace('\n', '').replace('\r', '')
        if '代號' in c_str and not code_col: code_col = c
        elif '名稱' in c_str and not name_col: name_col = c
        elif '投信' in c_str and '買賣超' in c_str and '金額' not in c_str and not trust_col: trust_col = c
        elif ('外資' in c_str or '外陸資' in c_str) and '買賣超' in c_str and '金額' not in c_str and not foreign_col: foreign_col = c
        elif '周轉率' in c_str and not turn_col: turn_col = c
            
    df_clean = pd.DataFrame()
    df_clean['代號'] = df[code_col].astype(str).str.strip() if code_col else ""
    df_clean['名稱'] = df[name_col].astype(str).str.strip() if name_col else ""
    df_clean = df_clean[df_clean['代號'].str.match(r'^\d{4}$')]
    
    def extract_and_clean(target_col):
        if target_col and target_col in df.columns:
            s = df[target_col].apply(clean_number)
            if '股' in str(target_col) or s.abs().max() > 20000:
                s = np.round(s / 1000, 0)
            return s.loc[df_clean.index]
        return pd.Series(0, index=df_clean.index)
        
    df_clean['投信買賣超'] = extract_and_clean(trust_col)
    df_clean['外資買賣超'] = extract_and_clean(foreign_col)
    df_clean['周轉率'] = extract_and_clean(turn_col)
    
    debug_info = {
        'filename': uploaded_file.name,
        'trust_col': trust_col,
        'trust_raw': df[trust_col].head(3).tolist() if trust_col else [],
        'trust_clean': df_clean['投信買賣超'].head(3).tolist()
    }
    return df_clean, debug_info

# ==========================================
# 模組四：側邊欄戰略控制台
# ==========================================
st.sidebar.header("⚙️ 戰術參數設定")
market_choice = st.sidebar.radio("🎯 掃描市場範圍", ["上市櫃全部", "僅上市", "僅上櫃"])
is_intraday = st.sidebar.checkbox("⚡ 啟用盤中狙擊模式", value=False)
st.sidebar.markdown("---")
min_trust_buy = st.sidebar.number_input("投信買超下限 (張)", value=100, step=50)
max_bias = st.sidebar.number_input("MA20 乖離率上限 (%)", value=5.0, step=0.5)
max_turnover = st.sidebar.number_input("周轉率上限 (%)", value=10.0, step=1.0)
vol_expansion = st.sidebar.number_input("溫和放量倍數", value=1.2, step=0.1)

st.sidebar.markdown("---")
uploaded_files = st.sidebar.file_uploader("📥 上傳籌碼 CSV", type="csv", accept_multiple_files=True)

df_universe = fetch_tw_universe()
df_chips = pd.DataFrame()

if uploaded_files:
    st.sidebar.markdown("### 🛠️ 戰情室除錯雷達")
    chip_dfs = []
    for f in uploaded_files:
        df_c, debug = parse_chip_csv(f)
        chip_dfs.append(df_c)
        st.sidebar.info(f"**檔案**: {debug['filename']}\n\n"
                        f"**抓到投信欄位**: {debug['trust_col']}\n\n"
                        f"**原始前三筆**: {debug['trust_raw']}\n\n"
                        f"**清洗後(張)**: {debug['trust_clean']}")
    df_chips = pd.concat(chip_dfs, ignore_index=True).drop_duplicates(subset=['代號'], keep='last')

# ==========================================
# 模組五：主程式掃描
# ==========================================
if st.button("🚀 啟動 V19.6 終極掃描"):
    with st.spinner("系統運作中..."):
        if not df_universe.empty and not df_chips.empty:
            df_master = pd.merge(df_universe, df_chips, on='代號', how='outer')
            df_master['名稱'] = df_master['名稱_y'].combine_first(df_master['名稱_x'])
            df_master['市場'] = df_master['市場'].fillna('未知')
        elif not df_chips.empty:
            df_master = df_chips.copy()
            df_master['市場'] = '未知'
        else:
            df_master = df_universe.copy()
            
        for col in ['投信買賣超', '外資買賣超', '周轉率']:
            if col not in df_master.columns: df_master[col] = 0
            df_master[col] = df_master[col].fillna(0)
            
        if market_choice == "僅上市": df_master = df_master[df_master['市場'].isin(['上市', '未知'])]
        elif market_choice == "僅上櫃": df_master = df_master[df_master['市場'].isin(['上櫃', '未知'])]
        
        df_to_scan = df_master[(df_master['投信買賣超'] >= min_trust_buy) & (df_master['外資買賣超'] > -1000)]
        
        if df_to_scan.empty:
            st.warning(f"⚠️ 條件下無股票通過初篩。")
            st.stop()

    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_stocks = len(df_to_scan)
    
    with st.spinner(f"正在進行技術面深度掃描 ({total_stocks} 檔)..."):
        for current_step, (idx, row) in enumerate(df_to_scan.iterrows()):
            stock_code = str(row['代號']).strip()
            market_type = row.get('市場', '上市')
            yf_code = f"{stock_code}.TWO" if market_type == '上櫃' else f"{stock_code}.TW"
            
            try:
                hist = yf.Ticker(yf_code).history(period="3mo")
                if len(hist) < 60 and market_type == '未知':
                    yf_code = f"{stock_code}.TWO"
                    hist = yf.Ticker(yf_code).history(period="3mo")
                    
                if len(hist) >= 60:
                    hist['MA20'] = hist['Close'].rolling(window=20).mean()
                    hist['MA60'] = hist['Close'].rolling(window=60).mean()
                    hist['MA5_Vol'] = hist['Volume'].rolling(window=5).mean()
                    
                    latest = hist.iloc[-1]
                    close_price = float(latest['Close'])
                    ma20 = float(latest['MA20'])
                    ma60 = float(latest['MA60'])
                    volume = float(latest['Volume']) / 1000
                    ma5_vol = float(latest['MA5_Vol']) / 1000
                    
                    bias_20 = ((close_price - ma20) / ma20) * 100
                    
                    if close_price > ma60 and bias_20 <= max_bias:
                        pass_volume = True
                        if not is_intraday:
                            if volume < (ma5_vol * vol_expansion): pass_volume = False
                            if row['周轉率'] > 0 and row['周轉率'] > max_turnover: pass_volume = False
                            
                        if pass_volume:
                            results.append({
                                '代號': stock_code, '名稱': row['名稱'], '市場': market_type,
                                '收盤價': round(close_price, 2), 'MA20_乖離率': round(bias_20, 2),
                                '投信買賣超': row['投信買賣超'], '外資買賣超': row['外資買賣超'],
                                '成交量': round(volume, 0), '5日均量': round(ma5_vol, 0)
                            })
            except Exception: pass
            
            progress_bar.progress((current_step + 1) / total_stocks)
            status_text.text(f"正在狙擊: {stock_code} ({current_step + 1}/{total_stocks})")
            
    progress_bar.empty()
    status_text.empty()
    
    df_final = pd.DataFrame(results)
    if not df_final.empty:
        capped_trust = df_final['投信買賣超'].clip(upper=2000)
        t_min, t_max = capped_trust.min(), capped_trust.max()
        df_final['投信分數'] = (capped_trust - t_min) / (t_max - t_min) * 60 if t_max > t_min else 60
            
        b_min, b_max = df_final['MA20_乖離率'].min(), df_final['MA20_乖離率'].max()
        df_final['乖離分數'] = (b_max - df_final['MA20_乖離率']) / (b_max - b_min) * 40 if b_max > b_min else 40
            
        df_final['綜合評分'] = np.round(df_final['投信分數'] + df_final['乖離分數'], 0)
        df_final = df_final.sort_values(by='綜合評分', ascending=False).reset_index(drop=True)
        
        def get_stars(score):
            if score >= 90: return '🌟🌟🌟🌟🌟'
            elif score >= 80: return '🌟🌟🌟🌟'
            elif score >= 70: return '🌟🌟🌟'
            else: return '🌟🌟'
            
        df_final['推薦星等'] = df_final['綜合評分'].apply(get_stars)
        display_cols = ['代號', '名稱', '市場', '收盤價', '綜合評分', '推薦星等', 'MA20_乖離率', '投信買賣超', '外資買賣超', '成交量', '5日均量']
        
        st.balloons()
        mode_text = "盤中狙擊模式" if is_intraday else "盤後嚴格模式"
        st.markdown(f"### 🎯 掃描完成！[{mode_text}] 共篩選出 {len(df_final)} 檔 S 級真龍")
        st.dataframe(df_final[display_cols])
        
        st.markdown("---")
        st.markdown("### 🤖 人機協同：一鍵呼叫 Manus 深度分析")
        prompt = f"我是指揮官。請幫我深度分析以下 {len(df_final)} 檔股票，著重基本面與 100 萬資金配置：\n\n"
        prompt += df_final[['代號', '名稱', '市場', '收盤價', '投信買賣超', '外資買賣超']].to_string(index=False)
        st.code(prompt, language="text")
    else:
        st.warning("⚠️ 未掃描到符合條件的標的，建議保留現金！")
