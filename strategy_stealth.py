import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import io
import time
import random

# ==========================================
# 🛠️ 核心工具函數 (獨立運作，不依賴其他模組)
# ==========================================
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

# ==========================================
# 🥷 潛伏妖股雷達主程式
# ==========================================
def run_stealth_radar(uploaded_csvs):
    st.markdown("### 🥷 V32 主力潛伏妖股雷達 (純淨無聲版)")
    st.caption("CIO 級過濾邏輯：排除法人雜訊、鎖定價格壓縮、尋找無量偷吃貨的特定主力標的。")
    
    if st.button("🔍 啟動潛伏掃描 (尋找沉睡巨龍)", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # --- 階段一：CSV 嫌疑犯海選 ---
        status_text.text("⏳ [1/3] 執行 CSV 內部迴圈：過濾法人雜訊...")
        all_data = []
        for file in uploaded_csvs:
            df = load_and_clean_csv(file)
            if df is None: continue
            col_code = find_column(df, ['證券代號', '代號', 'Code'])
            col_name = find_column(df, ['證券名稱', '名稱', 'Name'])
            col_trust = find_column(df, ['投信買賣超', '投信-買賣超', '投信買超', '投信買賣超股數'])
            
            if col_code and col_trust:
                df[col_code] = df[col_code].astype(str).str.replace('=', '').str.replace('"', '').str.strip()
                # 只保留 4 碼普通股
                df = df[df[col_code].str.match(r'^[1-9]\d{3}$', na=False)]
                df[col_trust] = pd.to_numeric(df[col_trust].astype(str).str.replace(',', ''), errors='coerce').fillna(0) / 1000.0
                
                temp_df = df[[col_code, col_name, col_trust]].copy()
                temp_df.columns = ['代號', '名稱', '投信買賣超']
                all_data.append(temp_df)
                
        if not all_data:
            st.error("❌ CSV 解析失敗或無資料。")
            return
            
        merged_df = pd.concat(all_data)
        # 🛡️ 核心過濾 1：投信買賣超介於 -100 到 +100 張之間 (無法人干擾)
        summary_df = merged_df.groupby(['代號', '名稱']).agg(總買超=('投信買賣超', 'sum')).reset_index()
        stealth_candidates = summary_df[(summary_df['總買超'] >= -100) & (summary_df['總買超'] <= 100)].copy()
        
        total_candidates = len(stealth_candidates)
        progress_bar.progress(20)
        
        # --- 階段二：YFinance 價格與動能 X 光 ---
        status_text.text(f"⏳ [2/3] 啟動 YFinance 引擎：對 {total_candidates} 檔嫌疑犯進行 K 線足跡掃描...")
        
        results = []
        stats = {"yf_fail": 0, "liq_fail": 0, "vol_fail": 0, "price_fail": 0, "squeeze_fail": 0}
        
        for i, (idx, row) in enumerate(stealth_candidates.iterrows()):
            code = row['代號']
            try:
                tkr = yf.Ticker(f"{code}.TW")
                hist = tkr.history(period="2mo")
                if hist.empty:
                    tkr = yf.Ticker(f"{code}.TWO")
                    hist = tkr.history(period="2mo")
                    
                if not hist.empty and len(hist) >= 20:
                    close = float(hist['Close'].iloc[-1])
                    prev_close = float(hist['Close'].iloc[-2])
                    
                    vol_today = float(hist['Volume'].iloc[-1]) / 1000
                    vol_5d = float(hist['Volume'].rolling(window=5).mean().iloc[-1]) / 1000 
                    if vol_5d == 0: vol_5d = 1 
                    
                    # 🛡️ 核心過濾 2：流動性底線 (5日均量 > 300張)
                    if vol_5d < 300:
                        stats["liq_fail"] += 1
                        continue
                        
                    # 🛡️ 核心過濾 3：溫和量能 (今日量比 0.5 ~ 1.5 倍)
                    vol_ratio = vol_today / vol_5d
                    if vol_ratio < 0.5 or vol_ratio > 1.5:
                        stats["vol_fail"] += 1
                        continue
                        
                    # 🛡️ 核心過濾 4：價格壓縮 (今日漲跌幅 -2% ~ +2%)
                    daily_change = ((close - prev_close) / prev_close) * 100
                    if abs(daily_change) > 2.0:
                        stats["price_fail"] += 1
                        continue
                        
                    # 🛡️ 核心過濾 5：布林壓縮 (近20日高低震幅 < 8%)
                    high_20 = float(hist['High'].rolling(window=20).max().iloc[-1])
                    low_20 = float(hist['Low'].rolling(window=20).min().iloc[-1])
                    amplitude_20d = ((high_20 - low_20) / low_20) * 100
                    if amplitude_20d > 8.0:
                        stats["squeeze_fail"] += 1
                        continue
                    
                    results.append({
                        "代號": code, 
                        "名稱": row['名稱'], 
                        "最新收盤": round(close, 2),
                        "今日漲跌(%)": round(daily_change, 2),
                        "今日量比": round(vol_ratio, 2),
                        "20日震幅(%)": round(amplitude_20d, 2),
                        "投信總買超(張)": int(row['總買超']),
                        "🎯 狀態": "🚨 完美潛伏"
                    })
                else:
                    stats["yf_fail"] += 1
            except:
                stats["yf_fail"] += 1
                
            # 擬人化延遲 (防 YF 封鎖)
            time.sleep(random.uniform(0.05, 0.15))
            progress_bar.progress(20 + int(((i + 1) / total_candidates) * 75))
            
        # --- 階段三：戰情報告呈現 ---
        status_text.text("⏳ [3/3] 彙整潛龍戰情報告...")
        progress_bar.progress(100)
        status_text.empty()
        
        st.session_state['stealth_results'] = results
        st.session_state['stealth_stats'] = stats

    # 顯示結果
    if 'stealth_results' in st.session_state:
        results = st.session_state['stealth_results']
        stats = st.session_state['stealth_stats']
        
        with st.expander("🛠️ 潛伏濾網擊殺報告 (點擊展開)", expanded=False):
            st.markdown(f"❌ **流動性不足 (殭屍股)**：`{stats['liq_fail']}` 檔")
            st.markdown(f"❌ **量能異常 (已發動/出貨)**：`{stats['vol_fail']}` 檔")
            st.markdown(f"❌ **單日波動過大**：`{stats['price_fail']}` 檔")
            st.markdown(f"❌ **20日震幅過大 (未壓縮)**：`{stats['squeeze_fail']}` 檔")
            st.markdown(f"✅ **最終存活潛龍**：`{len(results)}` 檔")
            
        if results:
            # 依照「20日震幅」由小到大排序 (震幅越小，吃貨嫌疑越大)
            final_df = pd.DataFrame(results).sort_values('20日震幅(%)', ascending=True).reset_index(drop=True)
            st.success(f"🎯 掃描完成！共抓出 {len(final_df)} 檔「無法人、量縮、價穩」的潛伏嫌疑犯。")
            st.dataframe(final_df, use_container_width=True)
            
            st.markdown("### 🎯 終極行動：送入狙擊槍查明真身")
            st.info("💡 點擊下方按鈕，系統會將這些嫌疑犯的代號，自動填入 Tab 5 的狙擊槍中！")
            
            # 提取所有代號，準備送入 Tab 5
            suspect_codes = final_df['代號'].tolist()
            codes_string = ",".join(suspect_codes)
            
            if st.button("🚀 一鍵將嫌疑犯送入 Tab 5 狙擊槍", type="primary", use_container_width=True):
                st.session_state['sniper_input'] = codes_string
                st.success("✅ 代號已成功載入狙擊槍！請切換至 **Tab 5 (主力 X 光狙擊)** 並按下發射按鈕！")
        else:
            st.warning("⚠️ 目前市場上沒有符合「完美潛伏」特徵的標的。主力可能都在休息，或已經全面發動。")
