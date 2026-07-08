import streamlit as st
import pandas as pd
import yfinance as yf
import concurrent.futures
import time

def clean_numeric(val):
    """清理 CSV 中的數字格式 (去除逗號)"""
    if isinstance(val, str):
        val = val.replace(',', '').strip()
    try:
        return float(val)
    except:
        return 0.0

def fetch_stock_data(ticker):
    """透過 yfinance 抓取個股 K 線數據 (支援上市與上櫃)"""
    try:
        # 先嘗試上市 (.TW)
        hist = yf.Ticker(f"{ticker}.TW").history(period="5d")
        if hist.empty:
            # 若無資料，嘗試上櫃 (.TWO)
            hist = yf.Ticker(f"{ticker}.TWO").history(period="5d")
            
        if not hist.empty and len(hist) >= 2:
            prev_close = hist['Close'].iloc[-2]
            today = hist.iloc[-1]
            return {
                'ticker': ticker,
                'open': today['Open'],
                'high': today['High'],
                'low': today['Low'],
                'close': today['Close'],
                'volume': today['Volume'] / 1000, # 轉換為「張」
                'prev_close': prev_close
            }
    except Exception:
        pass
    return None

def run_v33_scoring(df_aggregated, twii_pct):
    """執行 V33 三位一體動態積分運算"""
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
            vol = market_data['volume']
            if vol <= 0 or net_buy <= 0: continue 
            
            # 🎯 維度一：籌碼集中度 (滿分 40 分)
            concentration = (net_buy / vol) * 100
            if concentration > 15: score_c = 40
            elif concentration > 10: score_c = 30
            elif concentration > 5: score_c = 20
            elif concentration > 2: score_c = 10
            else: score_c = 0
            
            # 🎯 維度二：相對抗跌係數 RS (滿分 30 分)
            pct_change = (market_data['close'] - market_data['prev_close']) / market_data['prev_close'] * 100
            rs = pct_change - twii_pct
            if rs > 3: score_rs = 30
            elif rs > 1: score_rs = 20
            elif rs > -1: score_rs = 10
            else: score_rs = 0
            
            # 🎯 維度三：洗盤型態/下影線 (滿分 30 分)
            total_range = market_data['high'] - market_data['low']
            lower_shadow = min(market_data['open'], market_data['close']) - market_data['low']
            shadow_ratio = lower_shadow / total_range if total_range > 0 else 0
            
            if shadow_ratio > 0.6: score_p = 30
            elif shadow_ratio > 0.4: score_p = 20
            elif shadow_ratio > 0.2: score_p = 10
            else: score_p = 0
            
            # --- 總分與評級 ---
            total_score = score_c + score_rs + score_p
            if total_score >= 85: rating = "👑 S級真龍"
            elif total_score >= 70: rating = "🦅 A級潛龍"
            elif total_score >= 50: rating = "🛡️ B級觀察"
            else: rating = "淘汰"
            
            if total_score >= 50:
                results.append({
                    '評級': rating,
                    '總分': total_score,
                    '代號': str(row['代號']),
                    '名稱': row['名稱'],
                    '波段買超(張)': int(net_buy),
                    '今日成交(張)': int(vol),
                    '集中度(%)': round(concentration, 2),
                    '漲跌幅(%)': round(pct_change, 2),
                    '下影線比例': round(shadow_ratio, 2),
                    '籌碼分': score_c,
                    '抗跌分': score_rs,
                    '型態分': score_p
                })
                
    my_bar.empty() 
    return pd.DataFrame(results)

def render_v33_ui(uploaded_csvs):
    """渲染 V33 真龍雷達 UI"""
    st.header("👑 V33 真龍動態積分雷達 (3D 照妖鏡)")
    st.markdown("融合 **「籌碼集中度 + 相對抗跌係數 + 洗盤型態」**，從波段數據中精準抓出主力鎖碼的 S 級真龍！")
    
    if not uploaded_csvs:
        st.info("👈 請先從左側邊欄上傳 3~5 天的「法人買賣超 CSV」以啟動雷達。")
        return
        
    if st.button("🚀 啟動 V33 真龍積分運算", type="primary"):
        try:
            # 1. 讀取並合併所有 CSV (加入 Big5 雙語翻譯機)
            df_list = []
            for file in uploaded_csvs:
                try:
                    # 先嘗試國際標準 UTF-8
                    df_temp = pd.read_csv(file, encoding='utf-8')
                except UnicodeDecodeError:
                    # 若報錯，切換為台灣本土 Big5 編碼
                    file.seek(0) # 將檔案指標移回開頭
                    df_temp = pd.read_csv(file, encoding='big5', errors='ignore')
                df_list.append(df_temp)
                
            df_all = pd.concat(df_list, ignore_index=True)
            
            # 2. 尋找買賣超欄位並清理數據
            buy_col = next((col for col in df_all.columns if '買賣超' in col), None)
            if not buy_col:
                st.error("CSV 中找不到包含『買賣超』的欄位！請確認上傳的檔案格式。")
                return
                
            df_all[buy_col] = df_all[buy_col].apply(clean_numeric)
            
            # 3. 群組加總 (計算波段總買超)
            df_agg = df_all.groupby(['代號', '名稱'])[buy_col].sum().reset_index()
            df_agg = df_agg.rename(columns={buy_col: '買賣超'})
            df_agg = df_agg[df_agg['買賣超'] > 0] 
            
            st.success(f"✅ 成功融合 {len(uploaded_csvs)} 份 CSV，共篩選出 {len(df_agg)} 檔波段買超標的，準備聯網分析...")
            
            # 4. 抓取大盤基準
            twii = yf.Ticker("^TWII").history(period="5d")
            twii_pct = (twii['Close'].iloc[-1] - twii['Close'].iloc[-2]) / twii['Close'].iloc[-2] * 100
            st.info(f"📈 今日大盤基準漲跌幅：{twii_pct:.2f}%")
            
            # 5. 執行 V33 核心運算
            df_result = run_v33_scoring(df_agg, twii_pct)
            
            # 6. 顯示結果
            if not df_result.empty:
                df_result = df_result.sort_values(by='總分', ascending=False).reset_index(drop=True)
                st.balloons()
                st.subheader(f"🎯 掃描完成！共發現 {len(df_result)} 檔潛力標的")
                st.dataframe(df_result, use_container_width=True)
            else:
                st.warning("⚠️ 掃描完成，但今日無任何標的符合 V33 真龍標準 (總分 < 50)。請保持空手或觀察避險金庫！")
                
        except Exception as e:
            st.error(f"運算過程中發生錯誤: {e}")
