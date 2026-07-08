import streamlit as st
import pandas as pd
import yfinance as yf
import concurrent.futures
import io
import numpy as np

def clean_numeric(val):
    if pd.isna(val): 
        return 0.0
    if isinstance(val, str):
        val = val.replace(',', '').strip()
    try: 
        return float(val)
    except: 
        return 0.0

def fetch_stock_data(ticker):
    try:
        hist = yf.Ticker(f"{ticker}.TW").history(period="5d")
        if hist.empty:
            hist = yf.Ticker(f"{ticker}.TWO").history(period="5d")
            
        if not hist.empty and len(hist) >= 2:
            prev_close = hist['Close'].iloc[-2]
            today = hist.iloc[-1]
            vol_5d_sum = hist['Volume'].sum() / 1000 
            return {
                'ticker': ticker,
                'open': today['Open'],
                'high': today['High'],
                'low': today['Low'],
                'close': today['Close'],
                'volume_today': today['Volume'] / 1000, 
                'volume_5d': vol_5d_sum, 
                'prev_close': prev_close
            }
    except Exception: pass
    return None

def run_v33_scoring(df_aggregated, twii_pct):
    results = []
    progress_text = "🌐 V33 聯網雷達掃描中，請稍候..."
    my_bar = st.progress(0, text=progress_text)
    total_stocks = len(df_aggregated)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_row = {executor.submit(fetch_stock_data, str(row['代號'])): row for _, row in df_aggregated.iterrows()}
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_row):
            row = future_to_row[future]
            completed += 1
            my_bar.progress(completed / total_stocks, text=f"🌐 掃描進度: {completed}/{total_stocks} 檔")
            
            market_data = future.result()
            if not market_data: continue
            
            net_buy = row['買賣超']
            vol_today = market_data['volume_today']
            vol_5d = market_data['volume_5d']
            
            if vol_today < 500 or net_buy <= 0 or vol_5d <= 0: continue 
            
            concentration = (net_buy / vol_5d) * 100
            if concentration > 15: score_c = 40
            elif concentration > 10: score_c = 30
            elif concentration > 5: score_c = 20
            elif concentration > 2: score_c = 10
            else: score_c = 0
            
            pct_change = (market_data['close'] - market_data['prev_close']) / market_data['prev_close'] * 100
            rs = pct_change - twii_pct
            if rs > 3: score_rs = 30
            elif rs > 1: score_rs = 20
            elif rs > -1: score_rs = 10
            else: score_rs = 0
            
            total_range = market_data['high'] - market_data['low']
            lower_shadow = min(market_data['open'], market_data['close']) - market_data['low']
            shadow_ratio = lower_shadow / total_range if total_range > 0 else 0
            
            if shadow_ratio > 0.6: score_p = 30
            elif shadow_ratio > 0.4: score_p = 20
            elif shadow_ratio > 0.2: score_p = 10
            else: score_p = 0
            
            total_score = score_c + score_rs + score_p
            if total_score >= 85: rating = "👑 S級真龍"
            elif total_score >= 70: rating = "🦅 A級潛龍"
            else: rating = "淘汰"
            
            if total_score >= 70:
                results.append({
                    '評級': rating,
                    '總分': total_score,
                    '代號': str(row['代號']),
                    '名稱': row['名稱'],
                    '5日買超(張)': int(net_buy),
                    '5日集中度(%)': round(concentration, 2),
                    '今日漲跌(%)': round(pct_change, 2),
                    '下影線比例': round(shadow_ratio, 2),
                    '籌碼分': score_c,
                    '抗跌分': score_rs,
                    '型態分': score_p
                })
                
    my_bar.empty() 
    return pd.DataFrame(results)

def render_v33_ui(uploaded_csvs):
    st.header("👑 V33 真龍動態積分雷達 (3D 照妖鏡)")
    st.markdown("融合 **「波段集中度 + 相對抗跌係數 + 洗盤型態」**，從波段數據中精準抓出主力鎖碼的 S 級真龍！")
    
    if not uploaded_csvs:
        st.info("👈 請先從左側邊欄上傳 3~5 天的「法人買賣超 CSV」以啟動雷達。")
        return
        
    if st.button("🚀 啟動 V33 真龍積分運算", type="primary"):
        try:
            df_list = []
            for file in uploaded_csvs:
                file.seek(0)
                raw_data = file.read()
                try: decoded_content = raw_data.decode('utf-8')
                except UnicodeDecodeError: decoded_content = raw_data.decode('cp950', errors='ignore')
                
                lines = decoded_content.splitlines()
                header_idx = 0
                for i, line in enumerate(lines):
                    if '代號' in line or '代碼' in line:
                        header_idx = i
                        break
                
                df_temp = pd.read_csv(io.StringIO(decoded_content), skiprows=header_idx)
                df_temp.columns = df_temp.columns.str.strip().str.replace('"', '')
                df_list.append(df_temp)
                
            df_all = pd.concat(df_list, ignore_index=True)
            
            id_col = next((col for col in df_all.columns if '代號' in col or '代碼' in col), None)
            name_col = next((col for col in df_all.columns if '名稱' in col), None)
            
            buy_col = next((col for col in df_all.columns if '三大法人買賣超股數' in col), None)
            if not buy_col:
                buy_col = next((col for col in df_all.columns if '買賣超' in col), None)
            
            if not id_col or not name_col or not buy_col:
                st.error(f"❌ 找不到關鍵欄位！目前讀取到的欄位有：{list(df_all.columns)}")
                return
                
            df_all = df_all.rename(columns={id_col: '代號', name_col: '名稱', buy_col: '買賣超'})
            
            # 🧹 終極暴力清理：只留數字，且長度必須剛好是 4 碼 (純台股)
            df_all['代號'] = df_all['代號'].astype(str).str.replace(r'\D', '', regex=True)
            df_all = df_all[df_all['代號'].str.len() == 4]
            df_all = df_all[~df_all['代號'].str.startswith('00')]
            
            df_all['名稱'] = df_all['名稱'].astype(str).str.strip()
            df_all['買賣超'] = df_all['買賣超'].apply(clean_numeric) / 1000
            
            df_agg = df_all.groupby('代號').agg({'名稱': 'first', '買賣超': 'sum'}).reset_index()
            df_agg = df_agg[df_agg['買賣超'] > 0] 
            
            st.success(f"✅ 成功融合 {len(uploaded_csvs)} 份 CSV，剔除上萬檔權證與 ETF 後，共篩選出 {len(df_agg)} 檔純淨個股，準備聯網分析...")
            
            twii = yf.Ticker("^TWII").history(period="5d")
            twii_pct = (twii['Close'].iloc[-1] - twii['Close'].iloc[-2]) / twii['Close'].iloc[-2] * 100
            st.info(f"📈 今日大盤基準漲跌幅：{twii_pct:.2f}%")
            
            df_result = run_v33_scoring(df_agg, twii_pct)
            
            if not df_result.empty:
                df_result = df_result.sort_values(by='總分', ascending=False).reset_index(drop=True)
                st.balloons()
                st.subheader(f"🎯 掃描完成！經過嚴格篩選，僅存 {len(df_result)} 檔 S/A 級個股菁英")
                st.dataframe(df_result, use_container_width=True)
            else:
                st.warning("⚠️ 掃描完成，今日無任何個股達到 70 分以上的真龍標準。請保持空手！")
                
        except Exception as e:
            st.error(f"運算過程中發生錯誤: {e}")
