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

def run_radar(uploaded_csvs, filter_bias_max, filter_resonance, filter_vol_min):
    st.markdown("### 🧠 V28.1 雙腦評分雷達 (戰情透視版)...")
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
        col_trust = find_column(df, ['投信買賣超', '投信-買賣超', '投信買超', '投信買賣超股數'])
        
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
    
    top_candidates['所屬族群'] = top_candidates['代號'].map(lambda x: STOCK_SECTOR.get(x, "其他/未分類"))
    sector_counts = top_candidates[top_candidates['所屬族群'] != "其他/未分類"]['所屬族群'].value_counts()
    
    total_csv_stocks = len(top_candidates)
    progress_bar.progress(20)
    status_text.text(f"⏳ [2/3] 啟動 YFinance 引擎：檢驗 {total_csv_stocks} 檔標的...")
    
    results = []
    
    # 🛠️ 追蹤擊殺數據
    stats = {
        "yf_fail": 0,
        "vol_fail": 0,
        "bias_fail": 0,
        "reso_fail": 0
    }
    
    for i, (idx, row) in enumerate(top_candidates.iterrows()):
        code = row['代號']
        if len(code) != 4: 
            stats["yf_fail"] += 1
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
                    stats["vol_fail"] += 1
                    continue
                    
                # ⚠️ 這裡就是地板防線：bias_20 < 0.0 代表跌破月線
                if bias_20 < 0.0 or bias_20 > filter_bias_max:
                    stats["bias_fail"] += 1
                    continue
                    
                sector = row['所屬族群']
                resonance_count = sector_counts.get(sector, 1) if sector != "其他/未分類" else 1
                
                if filter_resonance and resonance_count < 3:
                    stats["reso_fail"] += 1
                    continue
                    
                bias_score = (filter_bias_max - bias_20) * 3
                trust_score = row['連買天數'] * 15
                resonance_bonus = resonance_count * 5 
                
                score = trust_score + bias_score + resonance_bonus
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
            else:
                stats["yf_fail"] += 1
        except:
            stats["yf_fail"] += 1
            
        progress_bar.progress(20 + int(((i + 1) / total_csv_stocks) * 75))
        
    status_text.text("⏳ [3/3] 彙整戰情報告...")
    progress_bar.progress(100)
    status_text.empty()
    
    # 🛠️ 顯示透視除錯報告
    with st.expander("🛠️ 雷達濾網擊殺報告 (點擊展開看真相)", expanded=True):
        st.markdown(f"**CSV 原始投信買超檔數**：`{total_csv_stocks}` 檔")
        st.markdown(f"❌ **無報價/連線失敗**：`{stats['yf_fail']}` 檔 *(YFinance 抓不到資料)*")
        st.markdown(f"❌ **流動性不足被殺**：`{stats['vol_fail']}` 檔 *(均量 < {filter_vol_min} 張)*")
        st.markdown(f"❌ **乖離率不符被殺**：`{stats['bias_fail']}` 檔 *(跌破月線 或 乖離 > {filter_bias_max}%)*")
        if filter_resonance:
            st.markdown(f"❌ **無族群共振被殺**：`{stats['reso_fail']}` 檔 *(孤鳥股)*")
        st.markdown(f"✅ **最終存活真龍**：`{len(results)}` 檔")
    
    if results:
        final_df = pd.DataFrame(results).sort_values('🔥 雙腦總分', ascending=False).reset_index(drop=True)
        st.success(f"🎯 掃描完成！共篩選出 {len(final_df)} 檔符合條件的標的。")
        st.dataframe(final_df, use_container_width=True)
    else:
        st.warning("⚠️ 經過嚴格的技術面與籌碼面濾網，本次沒有標的符合條件。請查看上方的「擊殺報告」了解原因。")
