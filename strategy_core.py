import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time
from datetime import datetime

def run_radar(uploaded_csvs, filter_bias_max, filter_resonance, filter_vol_min):
    st.subheader("👑 V35 終極勝率版：真龍雷達掃描")
    
    if not uploaded_csvs or len(uploaded_csvs) < 2:
        st.warning("⚠️ V35 引擎需要計算「點火加速度」，請至少上傳 2 天以上的 CSV (建議 5 天)。")
        return

    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # ==========================================
        # 📂 步驟一：解析並融合多日 CSV 數據
        # ==========================================
        status_text.text("📂 正在解析多日法人籌碼數據...")
        all_data = []
        
        for file in uploaded_csvs:
            # 讀取 CSV，嘗試不同編碼
            try:
                df = pd.read_csv(file, encoding='utf-8-sig')
            except:
                try:
                    file.seek(0)
                    df = pd.read_csv(file, encoding='cp950')
                except:
                    continue
            
            # 尋找關鍵欄位
            col_code = next((c for c in df.columns if '代號' in c or '代碼' in c), None)
            col_name = next((c for c in df.columns if '名稱' in c), None)
            col_foreign = next((c for c in df.columns if '外陸資買賣超' in c and '不含' in c), None)
            col_trust = next((c for c in df.columns if '投信買賣超' in c), None)
            col_dealer = next((c for c in df.columns if '自營商買賣超' in c and '自行' not in c and '避險' not in c), None)
            
            if not all([col_code, col_name, col_foreign, col_trust]):
                continue
                
            # 清理資料 (排除權證、ETF，代號長度為 4 的純股票)
            df[col_code] = df[col_code].astype(str).str.strip()
            df = df[df[col_code].str.len() == 4]
            df = df[df[col_code].str.isnumeric()]
            
            # 轉換為張數 (除以 1000)
            for col in [col_foreign, col_trust, col_dealer]:
                if col and col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0) / 1000
            
            # 統一欄位名稱
            df_clean = pd.DataFrame({
                '代號': df[col_code],
                '名稱': df[col_name],
                '外資買賣超': df[col_foreign],
                '投信買賣超': df[col_trust],
                '自營商買賣超': df[col_dealer] if col_dealer else 0
            })
            
            # 加上檔案日期標籤 (假設檔名包含日期，或依上傳順序)
            df_clean['File_Index'] = uploaded_csvs.index(file)
            all_data.append(df_clean)
            
        if not all_data:
            st.error("❌ 無法解析 CSV，請確認是否為證交所/櫃買中心下載的「三大法人買賣超日報」。")
            return
            
        # 合併所有資料
        df_all = pd.concat(all_data, ignore_index=True)
        
        # ==========================================
        # 🔥 步驟二：V35 核心邏輯 (點火加速度 & 護城河)
        # ==========================================
        status_text.text("🔥 正在計算籌碼點火加速度與鎖碼護城河...")
        progress_bar.progress(30)
        
        # 分離 Day 0 (最新一日) 與 Day 1~4 (過去幾日)
        # 假設 File_Index 0 是最新的一天
        df_day0 = df_all[df_all['File_Index'] == 0].groupby('代號').sum().reset_index()
        df_past = df_all[df_all['File_Index'] > 0].groupby('代號').sum().reset_index()
        
        # 計算過去平均 (除以過去的天數)
        past_days_count = len(uploaded_csvs) - 1
        if past_days_count > 0:
            df_past['外資買賣超'] = df_past['外資買賣超'] / past_days_count
            df_past['投信買賣超'] = df_past['投信買賣超'] / past_days_count
            
        # 準備篩選結果
        candidates = []
        
        for _, row0 in df_day0.iterrows():
            code = row0['代號']
            name = row0['名稱']
            
            # Day 0 數據
            d0_foreign = row0['外資買賣超']
            d0_trust = row0['投信買賣超']
            d0_dealer = row0['自營商買賣超']
            d0_main_force = d0_foreign + d0_trust # 波段主力 (白名單)
            
            # 過去數據
            past_row = df_past[df_past['代號'] == code]
            if not past_row.empty:
                past_main_force = past_row.iloc[0]['外資買賣超'] + past_row.iloc[0]['投信買賣超']
            else:
                past_main_force = 0
                
            # ------------------------------------------------
            # 🛡️ 濾網 1：鎖碼護城河比例 (波段主力 > 1.5倍 自營商)
            # ------------------------------------------------
            if d0_main_force <= 0: continue # 主力沒買，淘汰
            if d0_dealer > 0 and d0_main_force < (d0_dealer * 1.5): continue # 隔日沖/短線比例過高，淘汰
            
            # ------------------------------------------------
            # 🔥 濾網 2：籌碼點火加速度
            # ------------------------------------------------
            is_accel = False
            accel_score = 0
            
            # 條件 A：旱地拔蔥 (過去沒買或賣，今天突然大買 > 500張)
            if past_main_force <= 0 and d0_main_force >= 500:
                is_accel = True
                accel_score = 30
            # 條件 B：倍數點火 (過去有買，今天買超量是過去平均的 3 倍以上，且大於 300張)
            elif past_main_force > 0 and d0_main_force >= (past_main_force * 3) and d0_main_force >= 300:
                is_accel = True
                accel_score = 30
            # 條件 C：極端鎖碼 (今天單日買超大於 2000張，無視過去)
            elif d0_main_force >= 2000:
                is_accel = True
                accel_score = 20
                
            if not is_accel: continue # 沒有點火特徵，淘汰
            
            candidates.append({
                '代號': code,
                '名稱': name,
                '今日主力買超': round(d0_main_force, 0),
                '過去均買超': round(past_main_force, 0),
                '自營商買超': round(d0_dealer, 0),
                '點火分': accel_score
            })
            
        df_candidates = pd.DataFrame(candidates)
        
        if df_candidates.empty:
            status_text.text("⚠️ 今日無任何標的通過「點火加速度」與「護城河」考驗。")
            progress_bar.progress(100)
            return
            
        # ==========================================
        # 🎯 步驟三：聯網抓取 10MA 進行「成本貼合度」審查
        # ==========================================
        status_text.text(f"🎯 籌碼初選通過 {len(df_candidates)} 檔，正在聯網核對主力成本線 (10MA)...")
        progress_bar.progress(60)
        
        final_dragons = []
        total_cands = len(df_candidates)
        
        for i, row in df_candidates.iterrows():
            code = row['代號']
            # 嘗試抓取上市 (.TW) 或上櫃 (.TWO)
            ticker_tw = yf.Ticker(f"{code}.TW")
            hist = ticker_tw.history(period="1mo")
            if hist.empty:
                ticker_two = yf.Ticker(f"{code}.TWO")
                hist = ticker_two.history(period="1mo")
                
            if not hist.empty and len(hist) >= 10:
                current_price = hist['Close'].iloc[-1]
                ma10 = hist['Close'].tail(10).mean()
                
                # 計算乖離率
                bias_10ma = ((current_price - ma10) / ma10) * 100
                
                # ------------------------------------------------
                # 🎯 濾網 3：主力成本貼合度 (乖離率必須在 -2% ~ +5% 之間)
                # ------------------------------------------------
                if -2.0 <= bias_10ma <= filter_bias_max:
                    # 計算總分
                    cost_score = 40 if 0 <= bias_10ma <= 3 else 30 # 越貼合分數越高
                    anchor_score = 30 if row['自營商買超'] <= 0 else 20 # 沒有自營商干擾拿滿分
                    total_score = row['點火分'] + cost_score + anchor_score
                    
                    rating = "👑 S級真龍" if total_score >= 90 else "🦅 A級潛龍"
                    
                    final_dragons.append({
                        '評級': rating,
                        '總分': total_score,
                        '代號': code,
                        '名稱': row['名稱'],
                        '收盤價': round(current_price, 2),
                        '10MA乖離(%)': round(bias_10ma, 2),
                        '今日主力買超(張)': row['今日主力買超'],
                        '過去均買超(張)': row['過去均買超'],
                        '自營商買超(張)': row['自營商買超']
                    })
            
            # 防封鎖冷卻
            time.sleep(0.1)
            progress_bar.progress(60 + int(40 * (i / total_cands)))
            
        # ==========================================
        # 🏆 步驟四：產出 V35 終極戰報
        # ==========================================
        progress_bar.progress(100)
        status_text.text("✅ V35 終極掃描完成！")
        
        if final_dragons:
            df_final = pd.DataFrame(final_dragons)
            df_final = df_final.sort_values(by=['總分', '今日主力買超(張)'], ascending=[False, False]).reset_index(drop=True)
            
            st.success(f"🎯 歷經 V35 地獄級篩選，全市場僅存 **{len(df_final)}** 檔真龍！")
            st.dataframe(df_final, use_container_width=True)
            
            # 將結果存入 Session State 供其他模組使用
            st.session_state['v34_report'] = df_final
        else:
            st.warning("⚠️ 經過 10MA 成本貼合度審查，所有標的皆因「乖離過大(追高風險)」或「跌破均線」被淘汰。今日建議空手！")
            
    except Exception as e:
        st.error(f"V35 雷達運算發生錯誤: {e}")
        status_text.text("❌ 掃描中斷")
