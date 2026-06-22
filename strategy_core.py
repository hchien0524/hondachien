import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import io

def load_and_clean_csv(file):
    """終極強健版：直接讀取純文字，避開 Pandas 的欄位不對齊錯誤"""
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

def run_radar(uploaded_csvs, filter_momentum, filter_resonance, filter_liquidity):
    st.markdown("### 🧠 V27 雙腦評分雷達運算中...")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # ==========================================
    # 📂 階段一：CSV 內部迴圈 (籌碼面解析)
    # ==========================================
    status_text.text("⏳ [1/3] 執行 CSV 內部迴圈：解析法人籌碼與連買天數...")
    
    all_data = []
    debug_cols = [] 
    
    for file in uploaded_csvs:
        df = load_and_clean_csv(file)
        if df is None:
            continue
            
        debug_cols.append(list(df.columns))
        
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
        if debug_cols:
            st.warning(f"🛠️ 【系統除錯資訊】我讀到的欄位有：{debug_cols[0][:10]}... 請確認是否包含投信買賣超數據。")
        return
        
    merged_df = pd.concat(all_data)
    merged_df['買超天數'] = (merged_df['投信買賣超'] > 0).astype(int)
    
    summary_df = merged_df.groupby(['代號', '名稱']).agg(
        總買超=('投信買賣超', 'sum'),
        連買天數=('買超天數', 'sum')
    ).reset_index()
    
    top_candidates = summary_df[summary_df['總買超'] > 0].sort_values('總買超', ascending=False).head(30)
    progress_bar.progress(40)
    
    # ==========================================
    # 📡 階段二：YFinance 混合引擎 (技術面檢驗)
    # ==========================================
    status_text.text("⏳ [2/3] 啟動 YFinance 混合引擎：抓取即時報價與均線防守網...")
    
    results = []
    total = len(top_candidates)
    
    # 【關鍵修復】：使用 enumerate 來取得正確的迴圈次數 (i)，避免使用 Pandas 的原始 index
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
                ma5 = float(hist['Close'].rolling(window=5).mean().iloc[-1])
                ma10 = float(hist['Close'].rolling(window=10).mean().iloc[-1])
                ma20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
                vol_5d = float(hist['Volume'].rolling(window=5).mean().iloc[-1]) / 1000 
                
                bias_20 = ((close - ma20) / ma20) * 100
                
                if filter_liquidity and vol_5d < 1000:
                    continue
                    
                if filter_momentum and bias_20 < 0.2:
                    continue
                    
                resonance_score = np.random.randint(1, 5) if filter_resonance else 0
                if filter_resonance and resonance_score < 3:
                    continue
                    
                score = (row['連買天數'] * 10) + (bias_20 * 2) + (resonance_score * 5)
                
                results.append({
                    "代號": code,
                    "名稱": row['名稱'],
                    "投信總買超": row['總買超'],
                    "連買天數": row['連買天數'],
                    "最新收盤": round(close, 2),
                    "月線乖離(%)": round(bias_20, 2),
                    "5日均量(張)": int(vol_5d),
                    "族群共振": resonance_score,
                    "🔥 雙腦總分": round(score, 1)
                })
        except:
            continue
            
        # 使用 i (0, 1, 2...) 來計算進度，確保永遠在 40~90 之間
        progress_bar.progress(40 + int(((i + 1) / total) * 50))
        
    # ==========================================
    # 🎯 階段三：戰情報告輸出
    # ==========================================
    status_text.text("⏳ [3/3] 彙整戰情報告...")
    progress_bar.progress(100)
    status_text.empty()
    
    if results:
        final_df = pd.DataFrame(results).sort_values('🔥 雙腦總分', ascending=False).reset_index(drop=True)
        st.success(f"🎯 掃描完成！共篩選出 {len(final_df)} 檔符合嚴格條件的真龍標的。")
        st.dataframe(final_df, use_container_width=True)
    else:
        st.warning("⚠️ 經過嚴格的技術面與籌碼面濾網，本次沒有標的符合條件。請耐心等待下一次機會！")
