import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import io

try:
    from sector_dict import STOCK_SECTOR
except ImportError:
    STOCK_SECTOR = {}

def load_and_clean_csv(file):
    encodings = ['big5-hkscs', 'cp950', 'utf-8', 'utf-8-sig']
    file_bytes = file.getvalue() 
    
    for enc in encodings:
        try:
            text = file_bytes.decode(enc)
            lines = text.split('\n')
            
            header_idx = -1
            for i, line in enumerate(lines[:15]):
                if '代號' in line or '證券代號' in line:
                    header_idx = i
                    break
            
            if header_idx != -1:
                csv_data = '\n'.join(lines[header_idx:])
                df = pd.read_csv(io.StringIO(csv_data), dtype=str, skipinitialspace=True)
                df.columns = df.columns.str.strip().str.replace('"', '').str.replace(' ', '')
                return df
        except:
            continue
    return None

def find_column(df, keywords):
    for col in df.columns:
        for kw in keywords:
            if kw in str(col):
                return col
    return None

# 🛠️ V29.2 回呼函數：強制寫入記憶體
def add_targets_to_portfolio(selected_codes, default_cost, df):
    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = []
    for code in selected_codes:
        name = df[df['代號']==code]['名稱'].values[0]
        existing = next((item for item in st.session_state['portfolio'] if item.get("代號") == code), None)
        if existing:
            existing["成本價"] = default_cost 
        else:
            st.session_state['portfolio'].append({
                "代號": code,
                "名稱": name,
                "成本價": default_cost
            })

def run_radar(uploaded_csvs, filter_bias_max, filter_resonance, filter_vol_min):
    st.markdown("### 🧠 V29.3 終極雙腦評分雷達 (狀態記憶防閃退版)")
    
    # ==========================================
    # 1. 掃描引擎 (按下按鈕才執行，並將結果存入記憶體)
    # ==========================================
    if st.button("🚀 啟動雷達掃描", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("⏳ [1/3] 執行 CSV 內部迴圈：解析所有法人籌碼...")
        
        all_data = []
        for file in uploaded_csvs:
            df = load_and_clean_csv(file)
            if df is None: continue
                
            col_code = find_column(df, ['證券代號', '代號', 'Code'])
            col_name = find_column(df, ['證券名稱', '名稱', 'Name'])
            col_trust = find_column(df, ['投信買賣超', '投信-買賣超', '投信買超', '投信買賣超股數'])
            
            if col_code and col_trust:
                df[col_code] = df[col_code].astype(str).str.replace('=', '').str.replace('"', '').str.strip()
                df[col_trust] = pd.to_numeric(df[col_trust].astype(str).str.replace(',', ''), errors='coerce').fillna(0) / 1000.0
                
                temp_df = df[[col_code, col_name, col_trust]].copy()
                temp_df.columns = ['代號', '名稱', '投信買賣超']
                all_data.append(temp_df)
                
        if not all_data:
            st.error("❌ CSV 解析失敗：找不到『代號』或『投信買賣超』欄位。")
            return
            
        merged_df = pd.concat(all_data)
        merged_df['買超天數'] = (merged_df['投信買賣超'] > 0).astype(int)
        
        summary_df = merged_df.groupby(['代號', '名稱']).agg(
            總買超=('投信買賣超', 'sum'),
            連買天數=('買超天數', 'sum')
        ).reset_index()

        top_candidates = summary_df[summary_df['總買超'] > 0].copy()
        top_candidates['所屬族群'] = top_candidates['代號'].map(lambda x: STOCK_SECTOR.get(x, "其他/未分類"))
        sector_counts = top_candidates[top_candidates['所屬族群'] != "其他/未分類"]['所屬族群'].value_counts()
        
        total_csv_stocks = len(top_candidates)
        progress_bar.progress(20)
        status_text.text(f"⏳ [2/3] 啟動 YFinance 引擎：檢驗 {total_csv_stocks} 檔標的...")
        
        results = []
        stats = {"yf_fail": 0, "vol_fail": 0, "ma60_fail": 0, "bias_max_fail": 0, "reso_fail": 0}
        
        for i, (idx, row) in enumerate(top_candidates.iterrows()):
            code = row['代號']
            if len(code) != 4: 
                stats["yf_fail"] += 1
                continue
                
            try:
                tkr = yf.Ticker(f"{code}.TW")
                hist = tkr.history(period="6mo")
                if hist.empty:
                    tkr = yf.Ticker(f"{code}.TWO")
                    hist = tkr.history(period="6mo")
                    
                if not hist.empty and len(hist) >= 60:
                    close = float(hist['Close'].iloc[-1])
                    ma5 = float(hist['Close'].rolling(window=5).mean().iloc[-1])
                    ma10 = float(hist['Close'].rolling(window=10).mean().iloc[-1])
                    ma20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
                    ma60 = float(hist['Close'].rolling(window=60).mean().iloc[-1])
                    
                    vol_today = float(hist['Volume'].iloc[-1]) / 1000
                    vol_5d = float(hist['Volume'].rolling(window=5).mean().iloc[-1]) / 1000 
                    if vol_5d == 0: vol_5d = 1 
                    
                    if vol_5d < filter_vol_min:
                        stats["vol_fail"] += 1
                        continue
                        
                    if close < ma60:
                        stats["ma60_fail"] += 1
                        continue
                    
                    bias_20 = ((close - ma20) / ma20) * 100
                    if bias_20 > filter_bias_max:
                        stats["bias_max_fail"] += 1
                        continue
                        
                    sector = row['所屬族群']
                    resonance_count = sector_counts.get(sector, 1) if sector != "其他/未分類" else 1
                    if filter_resonance
