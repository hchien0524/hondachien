import pandas as pd
import yfinance as yf
import streamlit as st
import concurrent.futures

def fetch_price_and_ma(code):
    """抓取單檔股票收盤價與 MA20，自動判斷上市 (.TW) 或上櫃 (.TWO)"""
    for suffix in ['.TW', '.TWO']:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            # 只抓取最近一個月的資料來計算 MA20，加快速度
            hist = ticker.history(period="2mo")
            if not hist.empty and len(hist) >= 20:
                close = float(hist['Close'].iloc[-1])
                ma20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
                bias = ((close - ma20) / ma20) * 100
                return round(close, 2), round(ma20, 2), round(bias, 2)
        except:
            continue
    return None, None, None

def calculate_scores(df, min_trust, max_bias, mode):
    """
    雙大腦評分邏輯核心
    結合籌碼面 (投信/外資買超) 與 技術面 (MA20乖離率)
    V23.1 更新：分數正規化，平衡籌碼與技術面權重
    """
    # 1. 初步濾網：投信買超必須大於設定下限
    df_filtered = df[df['投信買賣超'] >= min_trust].copy()
    
    if df_filtered.empty:
        return pd.DataFrame()

    # 2. 抓取技術面資料 (使用多執行緒加速，極速獲取 MA20 與乖離率)
    st.info(f"⚡ 啟動技術面雷達：正在為 {len(df_filtered)} 檔標的計算 MA20 與乖離率...")
    
    results = []
    # 使用 10 個執行緒同時抓取 Yahoo Finance
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_code = {executor.submit(fetch_price_and_ma, row['代號']): row for _, row in df_filtered.iterrows()}
        for future in concurrent.futures.as_completed(future_to_code):
            row = future_to_code[future]
            close, ma20, bias = future.result()
            
            if close is not None:
                row_dict = row.to_dict()
                row_dict['收盤價'] = close
                row_dict['MA20'] = ma20
                row_dict['乖離率(%)'] = bias
                results.append(row_dict)

    if not results:
        return pd.DataFrame()

    df_tech = pd.DataFrame(results)

    # 3. 風險控管：剔除乖離率過高的危險標的
    df_tech = df_tech[df_tech['乖離率(%)'] <= max_bias].copy()

    if df_tech.empty:
        return pd.DataFrame()

    # 4. 雙大腦評分邏輯 (加入分數正規化，平衡籌碼與技術面權重)
    # 將張數除以 100，讓 1000 張 = 10 分
    trust_score = df_tech['投信買賣超'] / 100
    foreign_score = df_tech['外資買賣超'] / 100

    # 【短波突擊大腦】：重視籌碼爆發力 (投信與外資共鳴)
    df_tech['短波分數'] = (trust_score * 0.6) + (foreign_score * 0.4)
    
    # 【長線大底大腦】：重視低乖離與安全性 (乖離率越低，加分越多)
    df_tech['長線分數'] = (trust_score * 0.5) + ((max_bias - df_tech['乖離率(%)']) * 10)

    # 根據總司令選擇的模式，決定最終總分
    if mode == "短波突擊大腦":
        df_tech['總分'] = df_tech['短波分數']
    elif mode == "長線大底大腦":
        df_tech['總分'] = df_tech['長線分數']
    else: 
        # 【雙大腦交集】：兼具爆發力與安全性
        df_tech['總分'] = (df_tech['短波分數'] + df_tech['長線分數']) / 2

    # 5. 排序與整理最終戰報
    df_tech = df_tech.sort_values(by='總分', ascending=False)
    
    # 【UI 潔癖優化】：將買賣超張數強制轉為「整數」，去除煩人的小數點與 0
    df_tech['投信買賣超'] = df_tech['投信買賣超'].astype(int)
    df_tech['外資買賣超'] = df_tech['外資買賣超'].astype(int)
    
    # 其他技術指標與分數，嚴格四捨五入到小數點後 2 位
    df_tech = df_tech.round(2)
    
    # 嚴格定義輸出的欄位順序
    cols = ['代號', '名稱', '收盤價', 'MA20', '乖離率(%)', '投信買賣超', '外資買賣超', '總分']
    
    return df_tech[cols]
