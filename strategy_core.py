import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import io

# 嘗試載入 V28 產業字典
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

def run_radar(uploaded_csvs, filter_bias_max, filter_resonance, filter_vol_min):
    st.markdown("### 🧠 V28 雙腦評分雷達運算中 (族群共振啟動)...")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    status_text.text("⏳ [1/3] 執行 CSV 內部迴圈：解析所有法人籌碼...")
    
    all_data = []
    
    for file in uploaded_csvs:
        df = load_and_clean_csv(file)
        if df is None:
            continue
            
        col_code = find_column(df, ['證券代號', '代號', 'Code'])
        col_name = find_column(df, ['證券名稱', '名稱', 'Name'])
        col_trust = find_column(df, ['投信買賣超', '投信-買賣超', '投信買超'])
        
        if col_code and col_trust:
            df[col_code] = df[col_code].astype(str).str.replace('=', '').str.replace('"', '').str.strip()
            df[col_trust] = pd.to_numeric(df[col_trust].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
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
    
    # ==========================================
    # 🤝 啟動第二大腦：計算族群共振分數
    # ==========================================
    # 1. 幫每一檔股票貼上產業標籤
    top_candidates['所屬族群'] = top_candidates['代號'].map(lambda x: STOCK_SECTOR.get(x, "其他/未分類"))
    
    # 2. 計算每個族群在「投信買超名單」中出現的次數
    sector_counts = top_candidates[top_candidates['所屬族群'] != "其他/未分類"]['所屬族群'].value_counts()
    
    progress_bar.progress(20)
    status_text.text(f"⏳ [2/3] 啟動 YFinance 引擎：檢驗 {len(top_candidates)} 檔標的...")
    
    results = []
    total = len(top_candidates)
    
    for i, (idx, row) in enumerate(top_candidates.iterrows()):
        code = row['代號']
        if len(code) != 4: 
            continue
            
        try:
            tkr = yf.Ticker(f"{code}.TW")
            hist = tkr.history(period="1mo")
            if hist.empty:
                tkr = yf.Ticker(f"{code}.TWO")
                hist = tkr.history(period="1mo")
                
            if not hist.empty and len(hist) >= 20:
                close = float(hist['Close'].iloc[-1])
                ma20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
                vol_5d = float(hist['Volume'].rolling(window=5).mean().iloc[-1]) / 1000 
                
                bias_20 = ((close - ma20) / ma20) * 100
                
                if vol_5d < filter_vol_min:
                    continue
                    
                if bias_20 < 0.0 or bias_20 > filter_bias_max:
                    continue
                    
                # 取得該股票的族群共振次數 (至少為 1)
                sector = row['所屬族群']
                resonance_count = sector_counts.get(sector, 1) if sector != "其他/未分類" else 1
                
                # 🤝 嚴格族群濾網：如果打勾，則強制剔除沒有兄弟股(共振<3)的孤鳥
                if filter_resonance and resonance_count < 3:
                    continue
                    
                # 🧠 V28 終極計分法：籌碼 + 防禦 + 共振加成
                bias_score = (filter_bias_max - bias_20) * 3
                trust_score = row['連買天數'] * 15
                resonance_bonus = resonance_count * 5  # 每多一個兄弟股，加 5 分！
                
                score = trust_score + bias_score + resonance_bonus
                
                # 為了讓畫面好看，把族群名稱跟共振次數合併顯示
                display_resonance = f"{sector} ({resonance_count}檔)" if sector != "其他/未分類" else "無共振"
                
                results.append({
                    "代號": code,
                    "名稱": row['名稱'],
                    "投信總買超": row['總買超'],
                    "連買天數": row['連買天數'],
                    "最新收盤": round(close, 2),
                    "月線乖離(%)": round(bias_20, 2),
                    "5日均量(張)": int(vol_5d),
                    "🤝 族群共振": display_resonance,
                    "🔥 雙腦總分": round(score, 1)
                })
        except:
            pass
            
        progress_bar.progress(20 + int(((i + 1) / total) * 75))
        
    status_text.text("⏳ [3/3] 彙整戰情報告...")
    progress_bar.progress(100)
    status_text.empty()
    
    if results:
        final_df = pd.DataFrame(results).sort_values('🔥 雙腦總分', ascending=False).reset_index(drop=True)
        st.success(f"🎯 掃描完成！共篩選出 {len(final_df)} 檔符合條件的標的。")
        st.dataframe(final_df, use_container_width=True)
    else:
        st.warning("⚠️ 經過嚴格的技術面與籌碼面濾網，本次沒有標的符合條件。")
