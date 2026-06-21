import pandas as pd
import concurrent.futures
import requests
from datetime import datetime, timedelta
import streamlit as st
import time

def fetch_finmind_data(code, today_trust_buy, token=""):
    """
    V24.2 終極修復版：精準計算股本與連買天數 (解決時間差與 Token 問題)
    """
    # 【修復 1】：將 Token 正確附加在 URL 後方
    token_str = f"&token={token}" if token else ""
    
    end_date = datetime.now()
    start_date = (end_date - timedelta(days=45)).strftime('%Y-%m-%d')
    today_str = end_date.strftime('%Y-%m-%d')
    
    close, ma20, bias = None, None, None
    trust_ratio = 0.0
    consecutive_buy = 0
    recent_20_buy = 0
    
    try:
        # 1. 抓取股價與 MA20
        price_url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id={code}&start_date={start_date}{token_str}"
        res_price = requests.get(price_url, timeout=5 )
        if res_price.status_code == 200:
            data = res_price.json()
            if data.get('data'):
                df_price = pd.DataFrame(data['data'])
                if len(df_price) >= 20:
                    close = df_price['close'].iloc[-1]
                    ma20 = df_price['close'].rolling(window=20).mean().iloc[-1]
                    bias = ((close - ma20) / ma20) * 100

        # 2. 抓取投信籌碼
        chip_url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInstitutionalInvestorsBuySell&data_id={code}&start_date={start_date}{token_str}"
        res_chip = requests.get(chip_url, timeout=5 )
        if res_chip.status_code == 200:
            chip_data = res_chip.json()
            if chip_data.get('data'):
                df_chip = pd.DataFrame(chip_data['data'])
                df_trust = df_chip[df_chip['name'] == '投信'].copy()
                
                if not df_trust.empty:
                    df_trust['buy_sell'] = df_trust.get('buy', 0) - df_trust.get('sell', 0)
                    df_trust = df_trust.sort_values('date', ascending=False)
                    
                    latest_date = df_trust['date'].iloc[0]
                    
                    for val in df_trust['buy_sell']:
                        if val > 0:
                            consecutive_buy += 1
                        else:
                            break
                            
                    # 【修復 2】：解決 FinMind 延遲問題。如果 FinMind 最新資料不是今天，且 CSV 顯示今天有買超，則連買天數 +1
                    if latest_date != today_str and today_trust_buy > 0:
                        consecutive_buy += 1
                        
                    recent_20_buy = df_trust.head(20)['buy_sell'].sum()
                    if latest_date != today_str:
                        recent_20_buy += (today_trust_buy * 1000) # CSV 是張，轉成股

        # 3. 抓取發行股數 (使用 FinMind 股權分散表加總，最精準)
        share_url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockShareholding&data_id={code}&start_date={start_date}{token_str}"
        res_share = requests.get(share_url, timeout=5 )
        if res_share.status_code == 200:
            share_data = res_share.json()
            if share_data.get('data'):
                df_share = pd.DataFrame(share_data['data'])
                latest_share_date = df_share['date'].max()
                # 【修復 3】：將最新一週的所有持股級距加總，即為總發行股數
                total_shares = df_share[df_share['date'] == latest_share_date]['number_of_shares'].sum()
                
                if total_shares > 0:
                    trust_ratio = (recent_20_buy / total_shares) * 100

    except Exception as e:
        pass
        
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
    
    df_filtered = df[df['投信買賣超'] >= min_trust].copy()
    if df_filtered.empty:
        return pd.DataFrame()

    st.info(f"⚡ 啟動 FinMind 數據引擎：正在為 {len(df_filtered)} 檔標的進行深度 X 光掃描 (請稍候)...")
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # 【關鍵】：將 CSV 的今日買超張數 (row['投信買賣超']) 傳入引擎中
        future_to_code = {executor.submit(fetch_finmind_data, row['代號'], row['投信買賣超'], finmind_token): row for _, row in df_filtered.iterrows()}
