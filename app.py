import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import io
import requests

# ==========================================
# 模組一：系統初始化與 UI 框架
# ==========================================
st.set_page_config(page_title="HIOS Wave Radar V19", layout="wide")
st.title("🌊 HIOS Wave Radar V19 - 架構師完全體")
st.markdown("### 終極量化核心：全市場直連 × 智慧漏斗 × 動態時間軸")

# ==========================================
# 模組二：全市場名單獲取 (脫離 CSV 綁架)
# ==========================================
@st.cache_data(ttl=86400) # 快取一天，避免頻繁請求
def fetch_tw_universe():
    stocks = []
    # 1. 獲取上市名單 (TWSE OpenData)
    try:
        res_twse = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", timeout=5 )
        if res_twse.status_code == 200:
            for item in res_twse.json():
                if len(str(item.get('Code', ''))) == 4:
                    stocks.append({'代號': str(item['Code']), '名稱': str(item['Name']), '市場': '上市'})
    except: pass
    
    # 2. 獲取上櫃名單 (TPEx OpenData)
    try:
        res_tpex = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes", timeout=5 )
        if res_tpex.status_code == 200:
            for item in res_tpex.json():
                if len(str(item.get('SecuritiesCompanyCode', ''))) == 4:
                    stocks.append({'代號': str(item['SecuritiesCompanyCode']), '名稱': str(item['CompanyName']), '市場': '上櫃'})
    except: pass
    
    df_universe = pd.DataFrame(stocks)
    if df_universe.empty:
        # 終極備案：如果官方 API 斷線，提供基礎空表，後續由 CSV 補上
        return pd.DataFrame(columns=['代號', '名稱', '市場'])
    return df_universe.drop_duplicates(subset=['代號'])

# ==========================================
# 模組三：智慧資料清洗層 (Bulletproof CSV Parser)
# ==========================================
def parse_chip_csv(uploaded_file):
    raw_bytes = uploaded_file.read()
    decoded_text = None
    for enc in ['utf-8-sig', 'utf-8', 'cp950', 'big5']:
        try:
            decoded_text = raw_bytes.decode(enc)
            break
        except UnicodeDecodeError: continue
            
    if not decoded_text:
        decoded_text = raw_bytes.decode('cp950', errors='ignore')
        
    lines = decoded_text.splitlines()
    skip_rows = 0
    for i, line in enumerate(lines):
        if '代號' in line.replace(' ', '').replace('"', ''):
            skip_rows = i
            break
            
    df = pd.read_csv(io.StringIO(decoded_text), skiprows=skip_rows)
    df.columns = df.columns.str.strip()
    
    # 統一欄位名稱
    col_mapping = {
        '證券代號': '代號', '股票代號': '代號',
        '證券名稱': '名稱', '股票名稱': '名稱',
        '投信買賣超股數': '投信買賣超', 
        '外資買賣超股數': '外資買賣超',
        '外陸資買賣超股數(不含外資自營商)': '外資買賣超'
    }
    df = df.rename(columns=col_mapping)
    
    if '代號' in df.columns:
        df['代號'] = df['代號'].astype(str).str.strip()
        df = df[df['代號'].str.match(r'^\d{4}$')] # 純血普通股濾網
        
    # 暴力轉型與單位校正 (股 -> 張)
    for col in ['投信買賣超', '外資買賣超', '周轉率']:
        if col not in df.columns: df[col] = 0
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
        if df[col].abs().max() > 20000:
            df[col] = np.round(df[col] / 1000, 0)
            
    return df

# ==========================================
# 模組四：側邊欄戰略控制台
# ==========================================
st.sidebar.header("⚙️ 戰術參數設定")
market_choice = st.sidebar.radio("🎯 掃描市場範圍", ["上市櫃全部", "僅上市", "僅上櫃"])
strategy = st.sidebar.radio("🧠 選擇策略", ["A策略 (低乖離防守)", "B策略 (季線突破動能)"])

st.sidebar.markdown("---")
is_intraday = st.sidebar.checkbox("⚡ 啟用盤中狙擊模式", value=False, 
                                  help="盤中模式將自動放寬「周轉率」與「溫和放量」濾網，避免盤中資料失真。")

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ 絕對濾網 (Hard Filters)")
min_trust_buy = st.sidebar.number_input("投信買超下限 (張)", value=100, step=50)
max_bias = st.sidebar.number_input("MA20 乖離率上限 (%)", value=5.0, step=0.5)
max_turnover = st.sidebar.number_input("周轉率上限 (%)", value=10.0, step=1.0)
vol_expansion = st.sidebar.number_input("溫和放量倍數 (今日/5日均量)", value=1.2, step=0.1)

st.sidebar.markdown("---")
# V19 核心升級：支援多檔案同時上傳
uploaded_files = st.sidebar.file_uploader("📥 上傳籌碼 CSV (可同時框選上市+上櫃多個檔案)", type="csv", accept_multiple_files=True)

# ==========================================
# 模組五：雙軌時間軸引擎與主程式
# ==========================================
df_universe = fetch_tw_universe()

if st.button("🚀 啟動 V19 終極掃描"):
    with st.spinner("系統運作中：正在建構全市場名單與融合籌碼數據..."):
        # 1. 融合籌碼資料
        df_chips = pd.DataFrame()
        if uploaded_files:
            chip_dfs = [parse_chip_csv(f) for f in uploaded_files]
            df_chips = pd.concat(chip_dfs, ignore_index=True).drop_duplicates(subset=['代號'], keep='last')
        
        # 2. 結合全市場名單與籌碼
        if not df_universe.empty:
            df_master = pd.merge(df_universe, df_chips, on='代號', how='left')
            # 如果 CSV 有名稱但 Universe 沒有，補上名稱
            df_master['名稱'] = df_master['名稱_y'].combine_first(df_master['名稱_x'])
        else:
            df_master = df_chips.copy()
            df_master['市場'] = '未知'
            
        # 填補未上傳籌碼的空缺
        for col in ['投信買賣超', '外資買賣超', '周轉率']:
            if col not in df_master.columns: df_master[col] = 0
            df_master[col] = df_master[col].fillna(0)
            
        # 3. 市場範圍過濾
        if market_choice == "僅上市": df_master = df_master[df_master['市場'] == '上市']
        elif market_choice == "僅上櫃": df_master = df_master[df_master['市場'] == '上櫃']
        
        # 4. 智慧漏斗 (Pre-Filter)：先用籌碼過濾，大幅減少聯網時間 (3分鐘 -> 10秒)
        df_to_scan = df_master[(df_master['投信買賣超'] >= min_trust_buy) & (df_master['外資買賣超'] > -1000)]
        
        if df_to_scan.empty:
            st.warning(f"⚠️ 在「投信買超 >= {min_trust_buy} 張」且「外資未大賣」的條件下，沒有股票通過初篩。請確認是否已上傳最新 CSV，或調降標準。")
            st.stop()

    # 5. 聯網獲取技術指標
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_stocks = len(df_to_scan)
    
    with st.spinner(f"智慧漏斗啟動：已將目標縮減至 {total_stocks} 檔，正在進行技術面深度掃描..."):
        for current_step, (idx, row) in enumerate(df_to_scan.iterrows()):
            stock_code = str(row['代號']).strip()
            market_type = row.get('市場', '上市')
            yf_code = f"{stock_code}.TWO" if market_type == '上櫃' else f"{stock_code}.TW"
            
            try:
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
                    
                    # 技術面鐵門
                    if close_price > ma60 and bias_20 <= max_bias:
                        # 動態時間軸：盤後才嚴格檢查量能與周轉率
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
    
    # 6. 評分與輸出
    df_final = pd.DataFrame(results)
    if not df_final.empty:
        # 巨鯨擠壓效應校正 (設定天花板)
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
        mode_text = "盤中狙擊模式 (已放寬量能)" if is_intraday else "盤後嚴格模式 (全鐵門啟動)"
        st.markdown(f"### 🎯 掃描完成！[{mode_text}] 共篩選出 {len(df_final)} 檔 S 級真龍")
        st.dataframe(df_final[display_cols])
        
        # 人機協同戰情室
        st.markdown("---")
        st.markdown("### 🤖 人機協同：一鍵呼叫 Manus 深度分析")
        st.info("請點擊下方框框右上角的「複製」按鈕，將指令貼給 Manus 進行深度產業分析：")
        prompt = f"我是指揮官。請以頂級量化專家的身分，幫我深度分析以下 {len(df_final)} 檔通過 V19 嚴格濾網的股票。請著重於基本面、產業前景，並給我 100 萬資金的配置建議：\n\n"
        prompt += df_final[['代號', '名稱', '市場', '收盤價', '投信買賣超', '外資買賣超']].to_string(index=False)
        st.code(prompt, language="text")
    else:
        st.warning("⚠️ 在目前的嚴格濾網下，沒有股票符合條件。這代表目前盤勢可能不佳，
