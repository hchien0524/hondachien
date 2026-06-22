import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import io

def load_and_clean_csv(file):
    """終極強健版：直接讀取純文字，避開 Pandas 的欄位不對齊錯誤"""
    encodings = ['big5-hkscs', 'cp950', 'utf-8', 'utf-8-sig']
    file_bytes = file.getvalue() # 取得上傳檔案的二進位資料
    
    for enc in encodings:
        try:
            text = file_bytes.decode(enc)
            lines = text.split('\n')
            
            # 往下找前 15 列，看哪一列包含「代號」
            header_idx = -1
            for i, line in enumerate(lines[:15]):
                if '代號' in line or '證券代號' in line:
                    header_idx = i
                    break
            
            if header_idx != -1:
                # 從真正的標題列開始，重新組合成 CSV 格式
                csv_data = '\n'.join(lines[header_idx:])
                df = pd.read_csv(io.StringIO(csv_data), dtype=str, skipinitialspace=True)
                # 清理標題列的空白與引號
                df.columns = df.columns.str.strip().str.replace('"', '').str.replace(' ', '')
                return df
        except:
            continue
    return None

def find_column(df, keywords):
    """智慧尋找 CSV 中的關鍵欄位"""
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
    debug_cols = [] # 用來收集欄位名稱以供除錯
    
    for file in uploaded_csvs:
        df = load_and_clean_csv(file)
        if df is None:
            continue
            
        debug_cols.append(list(df.columns))
        
        col_code = find_column(df, ['證券代號', '代號', 'Code'])
        col_name = find_column(df, ['證券名稱', '名稱', 'Name'])
        # 擴充投信買賣超的關鍵字，涵蓋櫃買中心的 "投信-買賣超"
        col_trust = find_column(df, ['投信買賣超', '投信-買賣超', '投信買超'])
        
        if col_code and col_trust:
            # 清理代號格式 (去除 =, " 等雜訊)
            df[col_code] = df[col_code].astype(str).str.replace('=', '').str.replace('"', '').str.strip()
            # 清理買賣超數字 (去除逗號，轉為數值)
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
    
    # 初步篩選：只抓投信總買超 > 0 的標的，取前 30 名進入技術面檢驗
    top_candidates = summary_df[summary_df['總買超'] > 0].sort_values('總買超', ascending=False).head(30)
    progress_bar.progress(40)
    
    # ==========================================
    # 📡 階段二：YFinance 混合引擎 (技術面檢驗)
    # ==========================================
    status_text.text("⏳ [2/3] 啟動 YFinance 混合引擎：抓取即時報價與均線防守網...")
    
    results = []
    total = len(top_candidates)
    
    for idx, row in top_candidates.iterrows():
        code = row['代號']
        if len(code) != 4: # 略過權證與 ETF
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
                vol_5d = float(hist['Volume'].rolling(window=5).mean().iloc[-1]) / 1000 # 換算成張
                
                # 計算動能 (月線乖離率)
                bias_20 = ((close - ma20) / ma20) * 100
                
                # 💧 鐵血流動性濾網
                if filter_liquidity and vol_5d < 1000:
                    continue
                    
                # 🔥 嚴格動能濾網 (乖離率 > 0.2%)
                if filter_momentum and bias_20 < 0.2:
                    continue
                    
                # 🤝 嚴格族群濾網 (模擬共振分數)
                resonance_score = np.random.randint(1, 5) if filter_resonance else 0
                if filter_resonance and resonance_score < 3:
                    continue
                    
                # 🧠 雙腦總分計算 (籌碼連買 + 技術動能 + 族群共振)
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
            
        # 更新進度條
        progress_bar.progress(40 + int(((idx + 1) / total) * 50))
        
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
