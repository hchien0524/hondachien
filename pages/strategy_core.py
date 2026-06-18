import pandas as pd
import yfinance as yf
import numpy as np

def calculate_scores(df_chips, min_trust, max_bias):
    """負責抓取股價、計算均線、並給予多維度評分"""
    # 1. 第一道濾網：投信買超下限 (大幅節省運算時間)
    df_filtered = df_chips[df_chips['投信買賣超'] >= min_trust].copy()
    if df_filtered.empty:
        return pd.DataFrame()

    results = []
    
    # 2. 逐檔計算技術面與評分
    for index, row in df_filtered.iterrows():
        code = row['代號']
        # 預設先抓上市，若無資料則視為上櫃 (簡化版邏輯)
        ticker = f"{code}.TW"
        
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="3mo")
            if hist.empty:
                ticker = f"{code}.TWO"
                stock = yf.Ticker(ticker)
                hist = stock.history(period="3mo")
                
            if len(hist) < 20:
                continue
                
            close_price = hist['Close'].iloc[-1]
            ma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
            bias_20 = ((close_price - ma20) / ma20) * 100
            
            # 絕對防守線：乖離率過大直接剔除
            if bias_20 > max_bias:
                continue
                
            # 多維度評分引擎 (V20.3 邏輯)
            score = 0
            tags = []
            
            # 籌碼面 (滿分 40)
            if row['投信買賣超'] > 500: score += 40; tags.append("重金鎖碼")
            elif row['投信買賣超'] > 100: score += 30
            
            if row['外資買賣超'] > 0: score += 10; tags.append("土洋齊買")
            
            # 技術面 (滿分 30)
            if 0 < bias_20 <= 5: score += 30; tags.append("低乖離")
            elif 5 < bias_20 <= 10: score += 15
            
            # 基本面 (滿分 30，此處先給基礎分，未來可擴充營收 API)
            score += 20 
            
            results.append({
                '代號': code,
                '名稱': row['名稱'],
                '收盤價': round(close_price, 2),
                '總分': score,
                '籌碼力': score - 20 - (30 if 0 < bias_20 <= 5 else (15 if 5 < bias_20 <= 10 else 0)),
                '技術力': 30 if 0 < bias_20 <= 5 else (15 if 5 < bias_20 <= 10 else 0),
                '基本力': 20,
                '投信買賣超': row['投信買賣超'],
                '外資買賣超': row['外資買賣超'],
                '乖離率(%)': round(bias_20, 2),
                '戰術標籤': " | ".join(tags)
            })
            
        except Exception as e:
            continue
            
    if not results:
        return pd.DataFrame()
        
    df_results = pd.DataFrame(results)
    return df_results.sort_values('總分', ascending=False)
