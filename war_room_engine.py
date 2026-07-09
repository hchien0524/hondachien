import pandas as pd
import yfinance as yf
import time
import streamlit as st

def run_grand_unification(uploaded_csvs):
    if not uploaded_csvs or len(uploaded_csvs) < 2:
        st.error("⚠️ V35 終極引擎需要計算「點火加速度」，請至少上傳 2 天以上的 CSV (建議 3~5 天)。")
        return pd.DataFrame()

    my_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # ==========================================
        # 📂 步驟一：解析多日 CSV 數據
        # ==========================================
        status_text.text("📂 [1/3] 正在解析多日法人籌碼數據...")
        all_data = []
        for idx, file in enumerate(uploaded_csvs):
            try: df = pd.read_csv(file, encoding='utf-8-sig')
            except:
                file.seek(0)
                try: df = pd.read_csv(file, encoding='cp950')
                except: continue
            
            col_code = next((c for c in df.columns if '代號' in c or '代碼' in c), None)
            col_name = next((c for c in df.columns if '名稱' in c), None)
            col_foreign = next((c for c in df.columns if '外陸資買賣超' in c and '不含' in c), None)
            col_trust = next((c for c in df.columns if '投信買賣超' in c), None)
            col_dealer = next((c for c in df.columns if '自營商買賣超' in c and '自行' not in c and '避險' not in c), None)
            
            if not all([col_code, col_name, col_foreign, col_trust]): continue
            
            df[col_code] = df[col_code].astype(str).str.strip()
            df = df[df[col_code].str.len() == 4]
            df = df[df[col_code].str.isnumeric()]
            
            for col in [col_foreign, col_trust, col_dealer]:
                if col and col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0) / 1000
            
            df_clean = pd.DataFrame({
                '代號': df[col_code], '名稱': df[col_name],
                '外資買賣超': df[col_foreign], '投信買賣超': df[col_trust],
                '自營商買賣超': df[col_dealer] if col_dealer else 0
            })
            df_clean['File_Index'] = idx
            all_data.append(df_clean)
            
        if not all_data: return pd.DataFrame()
        df_all = pd.concat(all_data, ignore_index=True)
        
        # ==========================================
        # 🔥 步驟二：V35 點火加速度 & 鎖碼護城河
        # ==========================================
        status_text.text("🔥 [2/3] 正在計算籌碼點火加速度與鎖碼護城河...")
        my_bar.progress(30)
        
        df_day0 = df_all[df_all['File_Index'] == 0].groupby(['代號', '名稱']).sum().reset_index()
        df_past = df_all[df_all['File_Index'] > 0].groupby('代號').sum().reset_index()
        
        past_days_count = len(uploaded_csvs) - 1
        if past_days_count > 0:
            df_past['外資買賣超'] /= past_days_count
            df_past['投信買賣超'] /= past_days_count
            
        candidates = []
        for _, row0 in df_day0.iterrows():
            code, name = row0['代號'], row0['名稱']
            d0_main = row0['外資買賣超'] + row0['投信買賣超']
            d0_dealer = row0['自營商買賣超']
            
            past_row = df_past[df_past['代號'] == code]
            past_main = (past_row.iloc[0]['外資買賣超'] + past_row.iloc[0]['投信買賣超']) if not past_row.empty else 0
            
            # 🛡️ 護城河：波段主力必須大於自營商的 1.5 倍
            if d0_main <= 0: continue
            if d0_dealer > 0 and d0_main < (d0_dealer * 1.5): continue
            
            # 🔥 加速度：旱地拔蔥 或 倍數點火
            is_accel, accel_score = False, 0
            if past_main <= 0 and d0_main >= 500: is_accel, accel_score = True, 30
            elif past_main > 0 and d0_main >= (past_main * 3) and d0_main >= 300: is_accel, accel_score = True, 30
            elif d0_main >= 2000: is_accel, accel_score = True, 20
            
            if is_accel:
                candidates.append({'代號': code, '名稱': name, '今日主力買超': d0_main, '過去均買超': past_main, '自營商買超': d0_dealer, '點火分': accel_score})
                
        df_cands = pd.DataFrame(candidates)
        if df_cands.empty: return pd.DataFrame()
        
        # ==========================================
        # 🎯 步驟三：聯網核對 10MA 成本貼合度
        # ==========================================
        status_text.text(f"🎯 [3/3] 初選通過 {len(df_cands)} 檔，聯網核對主力成本線 (10MA)...")
        my_bar.progress(50)
        
        final_dragons = []
        total_cands = len(df_cands)
        for i, row in df_cands.iterrows():
            code = row['代號']
            hist = yf.Ticker(f"{code}.TW").history(period="1mo")
            if hist.empty: hist = yf.Ticker(f"{code}.TWO").history(period="1mo")
            
            if not hist.empty and len(hist) >= 10:
                curr_price = hist['Close'].iloc[-1]
                ma10 = hist['Close'].tail(10).mean()
                bias = ((curr_price - ma10) / ma10) * 100
                
                # 🎯 成本貼合度：乖離率必須在 -2% ~ +5% 之間
                if -2.0 <= bias <= 5.0:
                    cost_score = 40 if 0 <= bias <= 3 else 30
                    anchor_score = 30 if row['自營商買超'] <= 0 else 20
                    total_score = row['點火分'] + cost_score + anchor_score
                    rating = "👑 S級真龍" if total_score >= 90 else "🦅 A級潛龍"
                    
                    final_dragons.append({
                        '評級': rating, '總分': total_score, '代號': code, '名稱': row['名稱'],
                        '收盤價': round(curr_price, 2), '10MA乖離(%)': round(bias, 2),
                        '今日主力買超(張)': round(row['今日主力買超'], 0),
                        '過去均買超(張)': round(row['過去均買超'], 0),
                        '自營商買超(張)': round(row['自營商買超'], 0)
                    })
            time.sleep(0.1)
            my_bar.progress(50 + int(50 * (i / total_cands)))
            
        my_bar.progress(100)
        status_text.text("✅ V35 終極戰報生成完畢！")
        
        if final_dragons:
            df_final = pd.DataFrame(final_dragons).sort_values(by=['總分', '今日主力買超(張)'], ascending=[False, False])
            return df_final
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"戰情中心運算錯誤: {e}")
        return pd.DataFrame()
