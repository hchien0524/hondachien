import pandas as pd
import concurrent.futures
import requests
from datetime import datetime, timedelta
import streamlit as st
import time
import yfinance as yf

def fetch_finmind_data(code, token=""):
    """
    V24.2 終極修復版：FinMind 籌碼 + yfinance 極速股本查詢
    """
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    # 設定抓取區間 (過去 45 天，確保能算出 MA20 與近 20 日籌碼)
    end_date = datetime.now()
    start_date = (end_date - timedelta(days=45)).strftime('%Y-%m-%d')
    
    close, ma20, bias = None, None, None
    trust_ratio = 0.0
    consecutive_buy = 0
    
    try:
        # 1. 抓取股價與 MA20 (FinMind)
        price_url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id={code}&start_date={start_date}"
        res_price = requests.get(price_url, headers=headers, timeout=5 )
        if res_price.status_code == 200:
            data = res_price.json()
            if len(data.get('data', [])) > 0:
                df_price = pd.DataFrame(data['data'])
                if len(df_price) >= 20:
                    close = df_price['close'].iloc[-1]
                    ma20 = df_price['close'].rolling(window=20).mean().iloc[-1]
                    bias = ((close - ma20) / ma20) * 100

        # 2. 抓取投信籌碼 (FinMind)
        chip_url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInstitutionalInvestorsBuySell&data_id={code}&start_date={start_date}"
        res_chip = requests.get(chip_url, headers=headers, timeout=5 )
        if res_chip.status_code == 200:
            chip_data = res_chip.json()
            if len(chip_data.get('data', [])) > 0:
                df_chip = pd.DataFrame(chip_data['data'])
                df_trust = df_chip[df_chip['name'] == '投信'].copy()
                
                if not df_trust.empty:
                    # 【修復】：確保有 buy 和 sell 欄位並相減算出淨買賣超
                    if 'buy' in df_trust.columns and 'sell' in df_trust.columns:
                        df_trust['buy_sell'] = df_trust['buy'] - df_trust['sell']
                    elif 'buy_sell' not in df_trust.columns:
                        df_trust['buy_sell'] = 0
                        
                    df_trust = df_trust.sort_values('date', ascending=False)
                    
                    # 計算連買天數
                    for val in df_trust['buy_sell']:
                        if val > 0:
                            consecutive_buy += 1
                        else:
                            break
                    
                    # 計算近 20 日累積買超 (股)
                    recent_20_buy = df_trust.head(20)['buy_sell'].sum()
                    
                    # 3. 抓取發行股數 (改用 yfinance fast_info，極速且不耗 FinMind 額度)
                    try:
                        ticker = yf.Ticker(f"{code}.TW")
                        shares = ticker.fast_info.get('shares')
                        if not shares:
                            ticker = yf.Ticker(f"{code}.TWO")
                            shares = ticker.fast_info.get('shares')
                            
                        if shares and shares > 0:
                            # 計算近期投信買超佔股本比例 (%)
                            trust_ratio = (recent_20_buy / shares) * 100
                    except:
                        pass

    except Exception as e:
        pass
        
    # 稍微暫停，保護 API 不被封鎖
    time.sleep(0.2) 
    
    return (
        round(close, 2) if close else None, 
        round(ma20, 2) if ma20 else None, 
        round(bias, 2) if bias else None, 
        round(trust_ratio, 2), 
        consecutive_buy
    )

def calculate_scores(df, min_trust, max_bias, mode, finmind_token=""):
    """雙大腦評分邏輯核心"""
    
    # 1. 初步濾網：投信買超必須大於設定下限
    df_filtered = df[df['投信買賣超'] >= min_trust].copy()
    if df_filtered.empty:
        return pd.DataFrame()

    st.info(f"⚡ 啟動 FinMind 數據引擎：正在為 {len(df_filtered)} 檔標的進行深度 X 光掃描 (請稍候)...")
    
    results = []
    # 降低執行緒數量至 5，保護 API 不被封鎖
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_code = {executor.submit(fetch_finmind_data, row['代號'], finmind_token): row for _, row in df_filtered.iterrows()}
        for future in concurrent.futures.as_completed(future_to_code):
            row = future_to_code[future]
            close, ma20, bias, trust_ratio, consecutive_buy = future.result()
            
            if close is not None:
                row_dict = row.to_dict()
                row_dict['收盤價'] = close
                row_dict['MA20'] = ma20
                row_dict['乖離率(%)'] = bias
                row_dict['動能比例(%)'] = trust_ratio
                row_dict['連買天數'] = consecutive_buy
                
                # ==========================================
                # 🌟 戰術標籤 (備註) 生成邏輯 (已優化觸發條件)
                # ==========================================
                tags = []
                if trust_ratio >= 7.0:
                    tags.append("🔴 結帳警戒(>7%)")
                # 將黃金起漲區的門檻微調為 0.5%，因為大型股要買到 1% 其實非常多
                elif 0.5 <= trust_ratio < 7.0 and consecutive_buy >= 2:
                    tags.append("🟢 黃金起漲區")
                    
                if consecutive_buy >= 3:
                    tags.append(f"🔥 連買{consecutive_buy}天")
                    
                if bias is not None and bias <= 2.0:
                    tags.append("🛡️ 貼近月線")
                    
                row_dict['戰術標籤'] = " | ".join(tags) if tags else "一般"
                
                results.append(row_dict)

    if not results:
        return pd.DataFrame()

    df_tech = pd.DataFrame(results)

    # 3. 風險控管：剔除乖離率過高的危險標的
    df_tech = df_tech[df_tech['乖離率(%)'] <= max_bias].copy()
    if df_tech.empty:
        return pd.DataFrame()

    # 4. 雙大腦評分邏輯
    trust_score = df_tech['投信買賣超'] / 100
    foreign_score = df_tech['外資買賣超'] / 100

    df_tech['短波分數'] = (trust_score * 0.6) + (foreign_score * 0.4)
    df_tech['長線分數'] = (trust_score * 0.5) + ((max_bias - df_tech['乖離率(%)']) * 10)

    if mode == "短波突擊大腦":
        df_tech['總分'] = df_tech['短波分數']
    elif mode == "長線大底大腦":
        df_tech['總分'] = df_tech['長線分數']
    else: 
        df_tech['總分'] = (df_tech['短波分數'] + df_tech['長線分數']) / 2

    # 5. 排序與整理最終戰報
    df_tech = df_tech.sort_values(by='總分', ascending=False)
    
    df_tech['投信買賣超'] = df_tech['投信買賣超'].astype(int)
    df_tech['外資買賣超'] = df_tech['外資買賣超'].astype(int)
    df_tech = df_tech.round(2)
    
    # 加入新欄位
    cols = ['代號', '名稱', '收盤價', 'MA20', '乖離率(%)', '投信買賣超', '外資買賣超', '動能比例(%)', '連買天數', '總分', '戰術標籤']
    
    return df_tech[cols]
