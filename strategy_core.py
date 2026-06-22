import pandas as pd
import yfinance as yf
import streamlit as st
import concurrent.futures

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

def fetch_stock_data(code):
    """抓取單檔股票收盤價、MA20、乖離率、5日均量、產業分類與股本"""
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
                
                # 抓取股本 (用於計算動能比例)
                shares = ticker.info.get('sharesOutstanding', 0)
                capital_sheets = shares / 1000 if shares > 0 else 100000 # 預設10萬張防呆
                
                return round(close, 2), round(ma20, 2), round(bias, 2), round(vol5, 0), sector, capital_sheets
        except:
            continue
    return None, None, None, 0, "其他", 100000

def calculate_scores(df, min_trust, max_bias, max_price, min_volume, finmind_token=""):
    """
    終極 CSV 內循環引擎：動能校準版 (以動能比例取代絕對張數計分)
    """
    if df.empty:
        return pd.DataFrame()

    # ==========================================
    # 1. CSV 內循環聚合 (解決重複股票與連買天數)
    # ==========================================
    st.info("⚡ 階段一：啟動 CSV 內循環引擎，聚合多日籌碼資料...")
    
    # 將多天的 CSV 資料按股票代號合併
    df_grouped = df.groupby(['代號', '名稱']).agg(
        投信買賣超=('投信買賣超', 'sum'),
        外資買賣超=('外資買賣超', 'sum'),
        連買天數=('投信買賣超', lambda x: (x > 0).sum()) # 計算上傳的 CSV 中有幾天是買超
    ).reset_index()

    # 初步濾網：多日投信買超總和必須大於設定下限
    df_filtered = df_grouped[df_grouped['投信買賣超'] >= min_trust].copy()
    
    if df_filtered.empty:
        return pd.DataFrame()

    # ==========================================
    # 2. 抓取技術面、流動性與股本
    # ==========================================
    st.info(f"⚡ 階段二：啟動 yfinance 價格與流動性雷達，掃描 {len(df_filtered)} 檔標的...")
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_code = {executor.submit(fetch_stock_data, row['代號']): row for _, row in df_filtered.iterrows()}
        for future in concurrent.futures.as_completed(future_to_code):
            row = future_to_code[future]
            close, ma20, bias, vol5, sector, capital_sheets = future.result()
            
            # 嚴格執行：股價上限 + 乖離率濾網 + 5日均量流動性濾網
            if close is not None and close <= max_price and bias <= max_bias and vol5 >= min_volume:
                row_dict = row.to_dict()
                row_dict['產業'] = sector
                row_dict['收盤價'] = close
                row_dict['MA20'] = ma20
                row_dict['乖離率(%)'] = bias
                row_dict['5日均量'] = vol5
                
                # 計算動能比例 (投信總買超 / 股本)
                momentum = (row_dict['投信買賣超'] / capital_sheets) * 100 if capital_sheets > 0 else 0
                row_dict['動能比例(%)'] = round(momentum, 2)
                
                results.append(row_dict)

    if not results:
        return pd.DataFrame()

    df_final = pd.DataFrame(results)

    # ==========================================
    # 3. 🏆 終極暴力評分邏輯 (動能校準版)
    # ==========================================
    # 【關鍵修改】：以「動能比例 * 50」取代「張數 / 100」
    trust_score = df_final['動能比例(%)'] * 50
    bias_score = (max_bias - df_final['乖離率(%)']) * 10
    df_final['總分'] = trust_score + bias_score

    # 族群共振雷達
    sector_counts = df_final['產業'].value_counts()
    
    def get_tactical_tag(sector):
        count = sector_counts.get(sector, 0)
        if count >= 2 and sector != "其他":
            return f"🔥 族群共振 ({count}檔)"
        return "單兵突擊"
        
    df_final['戰術標籤'] = df_final['產業'].apply(get_tactical_tag)
    
    # 共振加分：同族群入榜，總分直接 +20 分
    df_final.loc[df_final['戰術標籤'].str.contains('族群共振'), '總分'] += 20

    # ==========================================
    # 4. 🧹 最終整理與輸出
    # ==========================================
    df_final = df_final.sort_values(by='總分', ascending=False)
    
    df_final['投信買賣超'] = df_final['投信買賣超'].astype(int)
    df_final['外資買賣超'] = df_final['外資買賣超'].astype(int)
    df_final['5日均量'] = df_final['5日均量'].astype(int)
    
    df_final = df_final.round(2)
    
    cols = ['代號', '名稱', '產業', '收盤價', '乖離率(%)', '5日均量', '投信買賣超', '外資買賣超', '動能比例(%)', '連買天數', '總分', '戰術標籤']
    
    return df_final[cols]
