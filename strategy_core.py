import pandas as pd
import concurrent.futures
import requests
from datetime import datetime, timedelta
import streamlit as st
import time
import yfinance as yf

# ==========================================
# 引擎一：yfinance 負責股價與 MA20 (免費用到飽)
# ==========================================
def fetch_yfinance_data(code):
    for suffix in ['.TW', '.TWO']:
        try:
            tkr = yf.Ticker(f"{code}{suffix}")
            hist = tkr.history(period="2mo")
            if not hist.empty and len(hist) >= 20:
                close = float(hist['Close'].iloc[-1])
                ma20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
                bias = ((close - ma20) / ma20) * 100
                return round(close, 2), round(ma20, 2), round(bias, 2)
        except:
            continue
    return None, None, None

# ==========================================
# 引擎二：FinMind 負責籌碼與股本 (加入 12 小時快取，極限省水)
# ==========================================
@st.cache_data(ttl=43200, show_spinner=False)
def fetch_finmind_cached(code, token):
    """只抓取歷史資料並快取，今日動態數據在外部計算"""
    token_str = f"&token={token}" if token else ""
    end_date = datetime.now()
    start_date = (end_date - timedelta(days=45)).strftime('%Y-%m-%d')
    
    recent_20_buy = 0
    consecutive_buy_hist = 0
    latest_date = ""
    total_shares = 0
    
    try:
        # 1. 抓取投信籌碼
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
                            consecutive_buy_hist += 1
                        else:
                            break
                    recent_20_buy = df_trust.head(20)['buy_sell'].sum()

        # 2. 抓取發行股數
        share_url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockShareholding&data_id={code}&start_date={start_date}{token_str}"
        res_share = requests.get(share_url, timeout=5 )
        if res_share.status_code == 200:
            share_data = res_share.json()
            if share_data.get('data'):
                df_share = pd.DataFrame(share_data['data'])
                latest_share_date = df_share['date'].max()
                total_shares = df_share[df_share['date'] == latest_share_date]['number_of_shares'].sum()
                
    except Exception as e:
        pass
        
    time.sleep(0.2) # 禮貌性延遲防封鎖
    return recent_20_buy, consecutive_buy_hist, latest_date, total_shares

def calculate_scores(df, min_trust, max_bias, mode, finmind_token=""):
    """雙大腦評分邏輯核心 (先斬後奏優化版)"""
    
    df_filtered = df[df['投信買賣超'] >= min_trust].copy()
    if df_filtered.empty:
        return pd.DataFrame()

    st.info(f"⚡ 階段一：啟動 yfinance 價格雷達，掃描 {len(df_filtered)} 檔標的...")
    
    # ==========================================
    # 階段一：先用免費的 yfinance 抓價格與乖離率
    # ==========================================
    price_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_code = {executor.submit(fetch_yfinance_data, row['代號']): row for _, row in df_filtered.iterrows()}
        for future in concurrent.futures.as_completed(future_to_code):
            row = future_to_code[future]
            close, ma20, bias = future.result()
            if close is not None:
                row_dict = row.to_dict()
                row_dict['收盤價'] = close
                row_dict['MA20'] = ma20
                row_dict['乖離率(%)'] = bias
                price_results.append(row_dict)
                
    if not price_results:
        return pd.DataFrame()
        
    df_price = pd.DataFrame(price_results)
    
    # 【關鍵防禦】：先用乖離率剔除危險標的，大幅減少 FinMind API 呼叫次數！
    df_price = df_price[df_price['乖離率(%)'] <= max_bias].copy()
    if df_price.empty:
        return pd.DataFrame()

    st.info(f"⚡ 階段二：啟動 FinMind 籌碼透視，對剩餘 {len(df_price)} 檔精銳進行深度分析...")
    
    # ==========================================
    # 階段二：只對「乖離率合格」的精銳呼叫 FinMind
    # ==========================================
    final_results = []
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    for _, row in df_price.iterrows():
        code = row['代號']
        today_trust_buy = row['投信買賣超']
        
        # 呼叫快取版的 FinMind (重複掃描不扣額度)
        recent_20_buy, consecutive_buy_hist, latest_date, total_shares = fetch_finmind_cached(code, finmind_token)
        
        # 動態計算今日數據
        consecutive_buy = consecutive_buy_hist
        final_recent_20 = recent_20_buy
        
        if latest_date != today_str and today_trust_buy > 0:
            consecutive_buy += 1
            final_recent_20 += (today_trust_buy * 1000)
            
        trust_ratio = 0.0
        if total_shares > 0:
            trust_ratio = (final_recent_20 / total_shares) * 100
            
        row_dict = row.to_dict()
        row_dict['動能比例(%)'] = round(trust_ratio, 2)
        row_dict['連買天數'] = consecutive_buy
        
        # 戰術標籤
        tags = []
        if trust_ratio >= 7.0:
            tags.append("🔴 結帳警戒(>7%)")
        elif 0.5 <= trust_ratio < 7.0 and consecutive_buy >= 2:
            tags.append("🟢 黃金起漲區")
            
        if consecutive_buy >= 3:
            tags.append(f"🔥 連買{consecutive_buy}天")
            
        if row_dict['乖離率(%)'] <= 2.0:
            tags.append("🛡️ 貼近月線")
            
        row_dict['戰術標籤'] = " | ".join(tags) if tags else "一般"
        final_results.append(row_dict)

    df_tech = pd.DataFrame(final_results)

    # 雙大腦評分邏輯
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

    df_tech = df_tech.sort_values(by='總分', ascending=False)
    df_tech['投信買賣超'] = df_tech['投信買賣超'].astype(int)
    df_tech['外資買賣超'] = df_tech['外資買賣超'].astype(int)
    df_tech = df_tech.round(2)
    
    cols = ['代號', '名稱', '收盤價', 'MA20', '乖離率(%)', '投信買賣超', '外資買賣超', '動能比例(%)', '連買天數', '總分', '戰術標籤']
    return df_tech[cols]
