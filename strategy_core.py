import pandas as pd
import yfinance as yf
import streamlit as st
import concurrent.futures
import requests
from datetime import datetime, timedelta

# 產業翻譯蒟蒻 (將 Yahoo 的英文產業分類轉為中文)
TRANSLATION_MAP = {
    "Technology": "電子工業",
    "Basic Materials": "原物料/化工",
    "Industrials": "工業/電機",
    "Consumer Cyclical": "消費循環",
    "Financial Services": "金融保險",
    "Consumer Defensive": "民生消費",
    "Healthcare": "醫療保健",
    "Communication Services": "通信網路",
    "Utilities": "公用事業",
    "Energy": "能源",
    "Real Estate": "建材營造"
}

def fetch_price_and_ma(code):
    """抓取單檔股票收盤價、MA20、乖離率、5日均量與產業分類"""
    for suffix in ['.TW', '.TWO']:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            hist = ticker.history(period="2mo")
            if not hist.empty and len(hist) >= 20:
                close = float(hist['Close'].iloc[-1])
                ma20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
                bias = ((close - ma20) / ma20) * 100
                
                # 計算 5 日均量 (張)
                vol5 = float(hist['Volume'].tail(5).mean() / 1000)
                
                # 抓取產業並翻譯
                raw_sector = ticker.info.get('sector', '其他')
                sector = TRANSLATION_MAP.get(raw_sector, raw_sector)
                
                return round(close, 2), round(ma20, 2), round(bias, 2), round(vol5, 0), sector
        except:
            continue
    return None, None, None, 0, "其他"

def fetch_finmind_data(code, today_trust_buy, token):
    """
    智慧回溯版：往前抓 15 天，徹底避開週末與國定假日陷阱，精準計算連買天數
    """
    try:
        # 1. 往前抓 15 天，確保一定能涵蓋到足夠的「交易日」
        start_date = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d")
        
        url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInstitutionalInvestorsBuySell&data_id={code}&start_date={start_date}"
        if token:
            url += f"&token={token}"
            
        res = requests.get(url, timeout=5 )
        if res.status_code != 200:
            return 0.0, 0  # API 壞掉或被擋
            
        data = res.json()
        if 'data' not in data or len(data['data']) == 0:
            return 0.0, 0
            
        df = pd.DataFrame(data['data'])
        
        # 2. 只篩選「投信」的資料
        df_trust = df[df['name'] == '投信'].copy()
        if df_trust.empty:
            return 0.0, 0
            
        # 3. 確保按日期由新到舊排序 (非常重要！)
        df_trust = df_trust.sort_values(by='date', ascending=False).reset_index(drop=True)
        
        # 4. 計算連買天數 (遇到賣超或 0 就中斷)
        consecutive_days = 0
        for val in df_trust['buy']:
            if val > 0:
                consecutive_days += 1
            else:
                break
                
        # 5. 計算動能比例 (近 3 個交易日的買超總和 / 股本)
        recent_3_days_buy = df_trust['buy'].head(3).sum()
        
        # 股本備援邏輯
        capital_sheets = 100000  # 預設 10 萬張防呆
        try:
            tkr = yf.Ticker(f"{code}.TW")
            shares = tkr.info.get('sharesOutstanding', 0)
            if shares > 0:
                capital_sheets = shares / 1000
        except:
            pass
            
        momentum = (recent_3_days_buy / capital_sheets) * 100 if capital_sheets > 0 else 0.0
        
        return round(momentum, 2), consecutive_days
        
    except Exception as e:
        return 0.0, 0

def calculate_scores(df, min_trust, max_bias, max_price, min_volume, finmind_token=""):
    """
    終極暴力評分核心：結合流動性濾網、股價上限、族群共振與智慧回溯籌碼
    """
    # 1. 初步濾網：投信買超必須大於設定下限
    df_filtered = df[df['投信買賣超'] >= min_trust].copy()
    
    if df_filtered.empty:
        return pd.DataFrame()

    st.info(f"⚡ 階段一：啟動 yfinance 價格與流動性雷達，掃描 {len(df_filtered)} 檔標的...")
    
    results = []
    # 使用多執行緒加速抓取技術面與產業資料
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_code = {executor.submit(fetch_price_and_ma, row['代號']): row for _, row in df_filtered.iterrows()}
        for future in concurrent.futures.as_completed(future_to_code):
            row = future_to_code[future]
            close, ma20, bias, vol5, sector = future.result()
            
            # 嚴格執行：股價上限 + 乖離率濾網 + 5日均量流動性濾網
            if close is not None and close <= max_price and bias <= max_bias and vol5 >= min_volume:
                row_dict = row.to_dict()
                row_dict['產業'] = sector
                row_dict['收盤價'] = close
                row_dict['MA20'] = ma20
                row_dict['乖離率(%)'] = bias
                row_dict['5日均量'] = vol5
                results.append(row_dict)

    if not results:
        return pd.DataFrame()

    df_tech = pd.DataFrame(results)

    st.info(f"⚡ 階段二：啟動 FinMind 籌碼透視，對剩餘 {len(df_tech)} 檔精銳進行深度分析...")
    
    finmind_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_code = {executor.submit(fetch_finmind_data, row['代號'], row['投信買賣超'], finmind_token): row for _, row in df_tech.iterrows()}
        for future in concurrent.futures.as_completed(future_to_code):
            row = future_to_code[future]
            momentum, consec_days = future.result()
            
            row_dict = row.to_dict()
            row_dict['動能比例(%)'] = momentum
            row_dict['連買天數'] = consec_days
            finmind_results.append(row_dict)

    df_final = pd.DataFrame(finmind_results)

    # ==========================================
    # 🏆 終極暴力評分邏輯
    # ==========================================
    # 1. 基礎分：籌碼張數 (100張=1分) + 低乖離加分
    trust_score = df_final['投信買賣超'] / 100
    bias_score = (max_bias - df_final['乖離率(%)']) * 10
    df_final['總分'] = trust_score + bias_score

    # 2. 族群共振雷達
    sector_counts = df_final['產業'].value_counts()
    
    def get_tactical_tag(sector):
        count = sector_counts.get(sector, 0)
        if count >= 2 and sector != "其他":
            return f"🔥 族群共振 ({count}檔)"
        return "單兵突擊"
        
    df_final['戰術標籤'] = df_final['產業'].apply(get_tactical_tag)
    
    # 3. 共振加分：同族群入榜，總分直接 +20 分
    df_final.loc[df_final['戰術標籤'].str.contains('族群共振'), '總分'] += 20

    # ==========================================
    # 🧹 最終整理與輸出
    # ==========================================
    df_final = df_final.sort_values(by='總分', ascending=False)
    
    df_final['投信買賣超'] = df_final['投信買賣超'].astype(int)
    df_final['外資買賣超'] = df_final['外資買賣超'].astype(int)
    df_final['5日均量'] = df_final['5日均量'].astype(int)
    
    df_final = df_final.round(2)
    
    cols = ['代號', '名稱', '產業', '收盤價', '乖離率(%)', '5日均量', '投信買賣超', '外資買賣超', '動能比例(%)', '連買天數', '總分', '戰術標籤']
    
    return df_final[cols]
