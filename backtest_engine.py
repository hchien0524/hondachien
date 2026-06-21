import pandas as pd
import yfinance as yf
import concurrent.futures
from datetime import datetime, timedelta
import streamlit as st

def simulate_trade(code, base_date_str, max_bias, max_price, trust_buy, foreign_buy):
    """單檔股票的時光機回測邏輯 (極簡總分版)"""
    base_date = pd.to_datetime(base_date_str)
    start_fetch = (base_date - timedelta(days=90)).strftime('%Y-%m-%d')
    end_fetch = (base_date + timedelta(days=40)).strftime('%Y-%m-%d')
    
    df_stock = pd.DataFrame()
    for suffix in ['.TW', '.TWO']:
        try:
            tkr = yf.Ticker(f"{code}{suffix}")
            hist = tkr.history(start=start_fetch, end=end_fetch)
            if not hist.empty:
                df_stock = hist
                break
        except:
            continue
            
    if df_stock.empty:
        return None
        
    df_stock.index = pd.to_datetime(df_stock.index).tz_localize(None).normalize()
    df_stock['MA20'] = df_stock['Close'].rolling(window=20).mean()
    df_stock['MA10'] = df_stock['Close'].rolling(window=10).mean()
    
    df_past = df_stock[df_stock.index <= base_date]
    if df_past.empty or len(df_past) < 20:
        return None
        
    base_close = float(df_past['Close'].iloc[-1])
    base_ma20 = float(df_past['MA20'].iloc[-1])
    
    if pd.isna(base_ma20) or base_ma20 == 0:
        return None
        
    # 1. 乖離率濾網
    bias = ((base_close - base_ma20) / base_ma20) * 100
    if bias > max_bias:
        return None
        
    # 2. 股價上限濾網
    if base_close > max_price:
        return None
        
    # 3. 外資倒貨否決權
    if foreign_buy < 0 and abs(foreign_buy) > trust_buy * 3:
        return None
        
    df_future = df_stock[df_stock.index > base_date].head(20)
    
    if df_future.empty:
        return {
            '代號': code, '基準日收盤': round(base_close, 2), '乖離率(%)': round(bias, 2),
            '進場價(隔日開盤)': 0, '出場價': 0, '最大漲幅(%)': 0, '區間報酬(%)': 0,
            '持有天數': 0, '出場原因': "⏳ 尚無未來數據"
        }
        
    entry_price = float(df_future['Open'].iloc[0])
    max_price_val = entry_price
    exit_price = float(df_future['Close'].iloc[-1])
    exit_reason = "⏳ 結算到期"
    hold_days = len(df_future)
    
    for i in range(len(df_future)):
        current_row = df_future.iloc[i]
        if current_row['High'] > max_price_val:
            max_price_val = current_row['High']
            
        if current_row['Close'] < current_row['MA10']:
            exit_price = current_row['Close']
            exit_reason = "🔴 跌破10MA"
            hold_days = i + 1
            break
            
    if entry_price > 0:
        ret_pct = ((exit_price - entry_price) / entry_price) * 100
        max_runup = ((max_price_val - entry_price) / entry_price) * 100
    else:
        ret_pct = 0
        max_runup = 0
    
    return {
        '代號': code,
        '基準日收盤': round(base_close, 2),
        '乖離率(%)': round(bias, 2),
        '進場價(隔日開盤)': round(entry_price, 2),
        '出場價': round(exit_price, 2),
        '最大漲幅(%)': round(max_runup, 2),
        '區間報酬(%)': round(ret_pct, 2),
        '持有天數': hold_days,
        '出場原因': exit_reason
    }

def run_batch_backtest(df_chip, base_date_str, min_trust, max_bias, max_price):
    """批次執行回測 (極簡總分版)"""
    df_filtered = df_chip[df_chip['投信買賣超'] >= min_trust].copy()
    if df_filtered.empty:
        return pd.DataFrame()
        
    st.info(f"⏳ 時光機啟動：正在對 {len(df_filtered)} 檔標的進行平行宇宙演算...")
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_code = {
            executor.submit(
                simulate_trade, 
                row['代號'], 
                base_date_str, 
                max_bias, 
                max_price,
                row['投信買賣超'], 
                row.get('外資買賣超', 0)
            ): row for _, row in df_filtered.iterrows()
        }
        for future in concurrent.futures.as_completed(future_to_code):
            row = future_to_code[future]
            res = future.result()
            if res is not None:
                res['名稱'] = row['名稱']
                res['投信買超'] = int(row['投信買賣超'])
                results.append(res)
                
    if not results:
        return pd.DataFrame()
        
    df_results = pd.DataFrame(results)
    cols = ['代號', '名稱', '投信買超', '乖離率(%)', '進場價(隔日開盤)', '出場價', '最大漲幅(%)', '區間報酬(%)', '持有天數', '出場原因']
    df_results = df_results[cols]
    df_results = df_results.sort_values(by='區間報酬(%)', ascending=False)
    
    return df_results
