import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import requests
import io
import re

# ==========================================
# 模組一：系統初始化與記憶體建構
# ==========================================
st.set_page_config(page_title="HIOS Wave Radar V20.2", layout="wide")
st.title("🌊 HIOS Wave Radar V20.2 - 競技場修復版")
st.markdown("### 終極量化核心：全樣本評分 × 多維度戰力分析")

if 'scan_results' not in st.session_state: st.session_state['scan_results'] = pd.DataFrame()
if 'portfolio' not in st.session_state: st.session_state['portfolio'] = []

# ==========================================
# 模組二：數據源革命 (API 直連 + CSV 備用)
# ==========================================
@st.cache_data(ttl=3600)
def fetch_api_data():
    df_list = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
    try:
        res = requests.get("https://openapi.twse.com.tw/v1/fund/T86_ALL", headers=headers, timeout=10 )
        if res.status_code == 200:
            df_twse = pd.DataFrame(res.json())
            df_twse = df_twse.rename(columns={'Code': '代號', 'Name': '名稱', 'ForeignInvestorDiff': '外資買賣超', 'InvestmentTrustDiff': '投信買賣超'})
            df_twse['市場'] = '上市'
            df_list.append(df_twse[['代號', '名稱', '市場', '外資買賣超', '投信買賣超']])
    except: pass

    try:
        res = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_fund", headers=headers, timeout=10 )
        if res.status_code == 200:
            df_tpex = pd.DataFrame(res.json())
            df_tpex = df_tpex.rename(columns={'SecuritiesCompanyCode': '代號', 'CompanyName': '名稱', 'ForeignInvestmentTrustDifference': '外資買賣超', 'InvestmentTrustDifference': '投信買賣超'})
            df_tpex['市場'] = '上櫃'
            df_list.append(df_tpex[['代號', '名稱', '市場', '外資買賣超', '投信買賣超']])
    except: pass

    if df_list:
        df_all = pd.concat(df_list, ignore_index=True)
        for col in ['外資買賣超', '投信買賣超']:
            df_all[col] = pd.to_numeric(df_all[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            df_all[col] = np.round(df_all[col] / 1000, 0)
        return df_all[df_all['代號'].str.match(r'^\d{4}$')]
    return pd.DataFrame()

def clean_number(val):
    if pd.isna(val): return 0
    val_str = str(val).strip()
    if val_str.startswith('(') and val_str.endswith(')'): val_str = '-' + val_str[1:-1]
    val_str = re.sub(r'[^\d\.-]', '', val_str)
    try: return float(val_str) if val_str else 0
    except: return 0

def parse_chip_csv(uploaded_file):
    uploaded_file.seek(0)
    raw_bytes = uploaded_file.read()
    decoded_text = None
    for enc in ['utf-8-sig', 'utf-8', 'cp950', 'big5']:
        try:
            decoded_text = raw_bytes.decode(enc)
            break
        except: continue
    if not decoded_text: decoded_text = raw_bytes.decode('cp950', errors='ignore')
    
    lines = decoded_text.splitlines()
    skip_rows = 0
    for i, line in enumerate(lines):
        if '代號' in line.replace(' ', '').replace('"', ''):
            skip_rows = i
            break
            
    df = pd.read_csv(io.StringIO(decoded_text), skiprows=skip_rows)
    
    trust_col, foreign_col, code_col, name_col = None, None, None, None
    for c in df.columns:
        c_str = str(c).replace(' ', '').replace('"', '').replace('\n', '').replace('\r', '')
        if '代號' in c_str and not code_col: code_col = c
        elif '名稱' in c_str and not name_col: name_col = c
        elif '投信' in c_str and '買賣超' in c_str and '金額' not in c_str and not trust_col: trust_col = c
        elif ('外資' in c_str or '外陸資' in c_str) and '買賣超' in c_str and '金額' not in c_str and not foreign_col: foreign_col = c
            
    df_clean = pd.DataFrame()
    df_clean['代號'] = df[code_col].astype(str).str.strip() if code_col else ""
    df_clean['名稱'] = df[name_col].astype(str).str.strip() if name_col else ""
    df_clean = df_clean[df_clean['代號'].str.match(r'^\d{4}$')]
    
    def extract_and_clean(target_col):
        if target_col and target_col in df.columns:
            s = df[target_col].apply(clean_number)
            if '股' in str(target_col) or s.abs().max() > 20000: s = np.round(s / 1000, 0)
            return s.loc[df_clean.index]
        return pd.Series(0, index=df_clean.index)
        
    df_clean['投信買賣超'] = extract_and_clean(trust_col)
    df_clean['外資買賣超'] = extract_and_clean(foreign_col)
    df_clean['市場'] = '未知'
    return df_clean

# ==========================================
# 模組三：側邊欄戰略控制台
# ==========================================
st.sidebar.header("⚙️ 戰術參數設定")
data_source = st.sidebar.radio("📡 數據來源", ["📁 手動 CSV 上傳 (備用)", "🌐 自動 API 直連 (推薦)"])
uploaded_files = None
if data_source == "📁 手動 CSV 上傳 (備用)":
    uploaded_files = st.sidebar.file_uploader("📥 上傳籌碼 CSV", type="csv", accept_multiple_files=True)

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ 評分門檻 (低於此分不顯示)")
min_total_score = st.sidebar.number_input("總分下限", value=30, step=5)

# ==========================================
# 模組四：主程式與多維度評分引擎
# ==========================================
tab1, tab2, tab3 = st.tabs(["🎯 戰情雷達 (掃描)", "⚔️ 策略競技場 (分析)", "🧠 記憶傳承 (存檔)"])

with tab1:
    if st.button("🚀 啟動 V20.2 全樣本掃描", type="primary"):
        with st.spinner("系統運作中：正在獲取籌碼數據..."):
            df_master = pd.DataFrame()
            if data_source == "🌐 自動 API 直連 (推薦)":
                df_master = fetch_api_data()
                if df_master.empty: st.error("❌ API 連線失敗，請改用 CSV 上傳備用方案。")
            elif uploaded_files:
                df_master = pd.concat([parse_chip_csv(f) for f in uploaded_files], ignore_index=True).drop_duplicates(subset=['代號'], keep='last')
            
            if df_master.empty: st.stop()
            
            # 移除嚴格初篩，只要有法人買賣就進入評分 (過濾掉完全沒動靜的死水股)
            df_to_scan = df_master[(df_master['投信買賣超'] > 0) | (df_master['外資買賣超'] > 0)]
            if df_to_scan.empty:
                st.warning("⚠️ 條件下無股票通過初篩。")
                st.stop()

        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_stocks = len(df_to_scan)
        
        with st.spinner(f"啟動多維度評分引擎，正在深度掃描 {total_stocks} 檔標的 (這可能需要幾分鐘)..."):
            for current_step, (idx, row) in enumerate(df_to_scan.iterrows()):
                stock_code = str(row['代號']).strip()
                market_type = row.get('市場', '上市')
                yf_code = f"{stock_code}.TWO" if market_type == '上櫃' else f"{stock_code}.TW"
                
                try:
                    ticker = yf.Ticker(yf_code)
                    hist = ticker.history(period="3mo")
                    if len(hist) < 60 and market_type == '未知':
                        yf_code = f"{stock_code}.TWO"
                        ticker = yf.Ticker(yf_code)
                        hist = ticker.history(period="3mo")
                        
                    if len(hist) >= 60:
                        hist['MA5'] = hist['Close'].rolling(window=5).mean()
                        hist['MA20'] = hist['Close'].rolling(window=20).mean()
                        hist['MA60'] = hist['Close'].rolling(window=60).mean()
                        hist['MA5_Vol'] = hist['Volume'].rolling(window=5).mean()
                        
                        latest = hist.iloc[-1]
                        close_price = float(latest['Close'])
                        ma5, ma20, ma60 = float(latest['MA5']), float(latest['MA20']), float(latest['MA60'])
                        volume = float(latest['Volume']) / 1000
                        ma5_vol = float(latest['MA5_Vol']) / 1000
                        
                        bias_20 = ((close_price - ma20) / ma20) * 100
                        
                        score_chip, score_tech, score_fund = 0, 0, 0
                        comments = []
                        
                        # 1. 籌碼力 (滿分 40)
                        trust_amt = (row['投信買賣超'] * close_price) / 10
                        if trust_amt > 50: score_chip += 20; comments.append("重金鎖碼")
                        elif trust_amt > 20: score_chip += 10
                        if row['外資買賣超'] > 0 and row['投信買賣超'] > 0: score_chip += 10; comments.append("土洋齊買")
                        if volume > 0 and (row['投信買賣超'] / volume) > 0.05: score_chip += 10; comments.append("高集中度")
                        
                        # 2. 技術力 (滿分 30)
                        ma_max, ma_min = max(ma5, ma20, ma60), min(ma5, ma20, ma60)
                        if (ma_max / ma_min) < 1.03: score_tech += 15; comments.append("均線糾結")
                        if 0 < bias_20 < 5: score_tech += 10; comments.append("低乖離")
                        if volume > (ma5_vol * 1.2): score_tech += 5; comments.append("溫和放量")
                        
                        # 3. 基本力 (滿分 30)
                        info = ticker.info
                        rev_growth = info.get('revenueGrowth', 0)
                        if rev_growth and rev_growth > 0.1: score_fund += 15; comments.append("營收雙位數成長")
                        elif rev_growth and rev_growth > 0: score_fund += 5
                        if info.get('profitMargins', 0) > 0.1: score_fund += 15; comments.append("高毛利")
                        
                        total_score = score_chip + score_tech + score_fund
                        
                        # 只保留總分大於門檻的股票
                        if total_score >= min_total_score:
                            results.append({
                                '代號': stock_code, '名稱': row['名稱'], '收盤價': round(close_price, 2),
                                '總分': total_score, '籌碼力(40)': score_chip, '技術力(30)': score_tech, '基本力(30)': score_fund,
                                '投信買超': row['投信買賣超'], '外資買超': row['外資買賣超'], 'MA20乖離(%)': round(bias_20, 2),
                                '系統短評': " | ".join(comments) if comments else "平穩"
                            })
                except Exception: pass
                
                progress_bar.progress((current_step + 1) / total_stocks)
                status_text.text(f"正在狙擊: {stock_code} ({current_step + 1}/{total_stocks})")
                
        progress_bar.empty()
        status_text.empty()
        
        df_final = pd.DataFrame(results)
        if not df_final.empty:
            df_final = df_final.sort_values(by='總分', ascending=False).reset_index(drop=True)
            st.session_state['scan_results'] = df_final
            st.balloons()
            st.success(f"✅ 掃描完成！共篩選出 {len(df_final)} 檔標的。")
        else:
            st.warning("⚠️ 未掃描到符合條件的標的。")

    if not st.session_state['scan_results'].empty:
        st.markdown("### 🎯 最新鎖定名單")
        st.dataframe(st.session_state['scan_results'])

# ==========================================
# 模組五：策略競技場
# ==========================================
with tab2:
    st.markdown("### ⚔️ 策略競技場：多維度戰力分析")
    if not st.session_state['scan_results'].empty:
        df_arena = st.session_state['scan_results']
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("#### 💰 籌碼霸主")
            st.dataframe(df_arena.sort_values('籌碼力(40)', ascending=False)[['代號', '名稱', '籌碼力(40)', '系統短評']].head(5))
        with col2:
            st.markdown("#### 📈 技術型態王")
            st.dataframe(df_arena.sort_values('技術力(30)', ascending=False)[['代號', '名稱', '技術力(30)', '系統短評']].head(5))
        with col3:
            st.markdown("#### 🏢 基本面護體")
            st.dataframe(df_arena.sort_values('基本力(30)', ascending=False)[['代號', '名稱', '基本力(30)', '系統短評']].head(5))
    else:
        st.info("💡 請先在「戰情雷達」執行掃描，競技場才能為您分析戰力！")

# ==========================================
# 模組六：記憶傳承系統
# ==========================================
with tab3:
    st.markdown("### 🧠 記憶傳承與戰情日誌")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 🛡️ 我的陣地 (持股備忘錄)")
        new_stock = st.text_input("新增持股 (例如：國產 33.8)")
        if st.button("➕ 加入陣地") and new_stock: st.session_state['portfolio'].append(new_stock)
        if st.session_state['portfolio']:
            for item in st.session_state['portfolio']: st.markdown(f"- 🎯 {item}")
            if st.button("🗑️ 清空陣地"): st.session_state['portfolio'] = []
            
    with col_b:
        st.markdown("#### 🤖 一鍵喚醒 Manus 銜接碼")
        prompt_text = f"Manus，我是指揮官。這是 V20 系統的記憶包。\n"
        prompt_text += f"【目前持股陣地】：{', '.join(st.session_state['portfolio']) if st.session_state['portfolio'] else '空手'}\n"
        prompt_text += f"【最新掃描名單 (前5名)】：\n"
        if not st.session_state['scan_results'].empty:
            prompt_text += st.session_state['scan_results'].head(5)[['代號', '名稱', '總分', '系統短評']].to_string(index=False)
        else: prompt_text += "無最新名單\n"
        prompt_text += "\n請讀取以上記憶，並接續我們的戰術，為我分析今日的 100 萬資金動作。"
        st.code(prompt_text, language="text")
