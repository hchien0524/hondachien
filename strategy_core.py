import pandas as pd
import yfinance as yf
import streamlit as st
import concurrent.futures
import requests
from datetime import datetime, timedelta

# 【新增】產業翻譯蒟蒻 (yfinance 英文對應台股分類)
SECTOR_MAPPING = {
    "Technology": "電子工業",
    "Basic Materials": "原物料/化工",
    "Consumer Cyclical": "消費循環",
    "Financial Services": "金融保險",
    "Industrials": "工業/電機",
    "Consumer Defensive": "民生消費",
    "Healthcare": "生技醫療",
    "Communication Services": "通信網路業",
    "Utilities": "公用事業",
    "Energy": "能源業",
    "Real Estate": "建材營造"
}

def fetch_finmind_data(code, trust_buy_today, token=""):
    """抓取 FinMind 籌碼數據，並搭便車抓取「產業類別」"""
    momentum_pct = 0.0
    continuous_days = 0
    industry = "未知"
    
    try:
        end_date = datetime.now()
        start_date = (end_date - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        headers = {'Authorization': f'Bearer {token}'} if token else {}
        
        # 1. 抓取歷史籌碼 (算連買天數)
        chip_url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInstitutionalInvestorsBuySell&data_id={code}&start_date={start_date}&end_date={end_date_str}"
        res_chip = requests.get(chip_url, headers=headers, timeout=5 )
        if res_chip.status_code == 200:
            chip_data = res_chip.json()
            if len(chip_data.get('data', [])) > 0:
                df_chip = pd.DataFrame(chip_data['data'])
                df_trust = df_chip[df_chip['name'] == '投信'].copy()
                if not df_trust.empty:
                    df_trust = df_trust.sort_values('date', ascending=False)
                    for val in df_trust['buy'] - df_trust['sell']:
                        if val > 0:
                            continuous_days += 1
                        else:
                            break
                            
        # 2. 抓取股票基本資料 (算動能比例 + 萃取產業類別)
        info_url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInfo&data_id={code}"
        res_info = requests.get(info_url, headers=headers, timeout=5 )
        if res_info.status_code == 200:
            info_data = res_info.json()
            if len(info_data.get('data', [])) > 0:
                shares_outstanding = info_data['data'][0].get('IssuedShares', 0)
                industry = info_data['data'][0].get('industry_category', '未知')
                if shares_outstanding > 0:
                    momentum_pct = round((trust_buy_today * 1000 / shares_outstanding) * 100, 2)
                    
    except Exception:
        pass
        
    return momentum_pct, continuous_days, industry

def fetch_price_and_ma(code):
    """抓取收盤價、MA20、5日均量"""
    for suffix in ['.TW', '.TWO']:
        try:
            tkr = yf.Ticker(f"{code}{suffix}")
            hist = tkr.history(period="2mo")
            if not hist.empty and len(hist) >= 20:
                close = float(hist['Close'].iloc[-1])
                ma20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
                bias = ((close - ma20) / ma20) * 100
                vol_5ma = float(hist['Volume'].rolling(window=5).mean().iloc[-1]) / 1000
                return round(close, 2), round(ma20, 2), round(bias, 2), round(vol_5ma, 0), suffix
        except:
            continue
    return None, None, None, None, None

def process_stock(row, token):
    """單檔股票處理流"""
    code = row['代號']
    trust_buy = row['投信買賣超']
    
    close, ma20, bias, vol_5ma, suffix = fetch_price_and_ma(code)
    if close is None:
        return None
        
    mom_pct, days, industry = fetch_finmind_data(code, trust_buy, token)
    
    # yfinance 備援機制
    if mom_pct == 0 and suffix is not None:
        try:
            tkr = yf.Ticker(f"{code}{suffix}")
            info = tkr.info
            shares = info.get('sharesOutstanding', 0)
            if shares > 0:
                mom_pct = round((trust_buy * 1000 / shares) * 100, 2)
            # 若 FinMind 沒抓到產業，用 yfinance 的英文產業別頂替，並套用翻譯蒟蒻
            if industry == "未知":
                yf_sector = info.get('sector', '')
                if yf_sector: 
                    industry = SECTOR_MAPPING.get(yf_sector, yf_sector)
        except:
            pass

    row_dict = row.to_dict()
    row_dict['產業類別'] = industry
    row_dict['收盤價'] = close
    row_dict['MA20'] = ma20
    row_dict['乖離率(%)'] = bias
    row_dict['5日均量(張)'] = vol_5ma
    row_dict['動能比例(%)'] = mom_pct
    row_dict['連買天數'] = days
    return row_dict

def calculate_scores(df, min_trust, max_bias, max_price, min_volume, token=""):
    """終極單一總分演算引擎 (加入族群共振雷達與翻譯蒟蒻)"""
    df_filtered = df[df['投信買賣超'] >= min_trust].copy()
    if df_filtered.empty: return pd.DataFrame()

    st.info(f"⚡ 啟動量化引擎：正在對 {len(df_filtered)} 檔標的進行深度運算...")
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_code = {executor.submit(process_stock, row, token): row for _, row in df_filtered.iterrows()}
        for future in concurrent.futures.as_completed(future_to_code):
            res = future.result()
            if res is not None:
                results.append(res)

    if not results: return pd.DataFrame()
    df_res = pd.DataFrame(results)

    # 1. 基礎濾網
    df_res = df_res[df_res['乖離率(%)'] <= max_bias]
    df_res = df_res[df_res['收盤價'] <= max_price]
    df_res = df_res[df_res['5日均量(張)'] >= min_volume]
    
    if '外資買賣超' not in df_res.columns:
        df_res['外資買賣超'] = 0
    dump_condition = (df_res['外資買賣超'] < 0) & (df_res['外資買賣超'].abs() > df_res['投信買賣超'] * 3)
    df_res = df_res[~dump_condition]

    if df_res.empty: return pd.DataFrame()

    # 2. 🏆 基礎總分演算
    base_score = (df_res['投信買賣超'] / 100 * 0.6) + (df_res['外資買賣超'] / 100 * 0.4)
    mom_score = df_res['動能比例(%)'] * 50
    def_score = (max_bias - df_res['乖離率(%)']) * 10
    df_res['🏆 總分'] = base_score + mom_score + def_score
    
    # 3. 🔥 族群共振雷達 (核心邏輯)
    df_res['戰術標籤'] = "單兵突擊"
    # 計算各產業出現的次數 (排除未知)
    sector_counts = df_res[df_res['產業類別'] != '未知']['產業類別'].value_counts()
    
    for idx, row in df_res.iterrows():
        sec = row['產業類別']
        if sec != '未知' and sector_counts.get(sec, 0) >= 2:
            count = sector_counts[sec]
            df_res.at[idx, '戰術標籤'] = f"🔥 族群共振 ({count}檔)"
            df_res.at[idx, '🏆 總分'] += 20  # 【重賞】同族群直接加 20 分！
            
    # 4. 排序與格式化
    df_res = df_res.sort_values(by='🏆 總分', ascending=False).round(2)
    df_res['投信買賣超'] = df_res['投信買賣超'].astype(int)
    df_res['外資買賣超'] = df_res['外資買賣超'].astype(int)
    df_res['連買天數'] = df_res['連買天數'].astype(int)
    df_res['5日均量(張)'] = df_res['5日均量(張)'].astype(int)

    cols = ['代號', '名稱', '產業類別', '收盤價', '乖離率(%)', '5日均量(張)', '投信買賣超', '外資買賣超', '動能比例(%)', '連買天數', '🏆 總分', '戰術標籤']
    return df_res[cols]
