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
    token_str = f"&token={token}" if token else ""
    end_date = datetime.now()
    start_date = (end_date - timedelta(days=45)).strftime('%Y-%m-%d')
    
    recent_20_buy = 0
    consecutive_buy_hist = 0
    latest_date = ""
    total_shares = 0
    
    try:
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
        
    time.sleep(0.2) 
    return recent_20_buy, consecutive_buy_hist, latest_date, total_shares

def calculate_scores(df, min_trust, max_bias, finmind_token=""):
    """投顧級戰術分群核心 (一鍵全掃版)"""
    
    df_filtered = df[df['投信買賣超'] >= min_trust].copy()
    if df_filtered.empty:
        return pd.DataFrame()

    st.info(f"⚡ 階段一：啟動 yfinance 價格雷達，掃描 {len(df_filtered)} 檔標的...")
    
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
    df_price = df_price[df_price['乖離率(%)'] <= max_bias].copy()
    if df_price.empty:
        return pd.DataFrame()

    st.info(f"⚡ 階段二：啟動 FinMind 籌碼透視，對剩餘 {len(df_price)} 檔精銳進行深度分析...")
    
    final_results = []
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    for _, row in df_price.iterrows():
        code = row['代號']
        today_trust_buy = row['投信買賣超']
        foreign_buy = row['外資買賣超']
        bias = row['乖離率(%)']
        
        recent_20_buy, consecutive_buy_hist, latest_date, total_shares = fetch_finmind_cached(code, finmind_token)
        
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
        
        # ==========================================
        # 🌟 雙維度評分系統
        # ==========================================
        # 爆發力：純看籌碼張數 (投信權重較高)
        exp_score = (today_trust_buy * 0.6 + foreign_buy * 0.4) / 100
        row_dict['🔥 爆發力'] = round(exp_score, 1)
        
        # 防禦力：純看乖離率 (離月線越近分數越高，最高 100 分)
        def_score = max(0, (max_bias - bias) * (100 / max_bias)) if max_bias > 0 else 0
        row_dict['🛡️ 防禦力'] = round(def_score, 1)
        
        # ==========================================
        # 🎯 AI 戰術象限分類
        # ==========================================
        # 定義高爆發：投信買超 > 800張 或 爆發力 > 8
        is_high_exp = (today_trust_buy >= 800) or (exp_score >= 8.0)
        # 定義高防禦：乖離率 <= 2.5%
        is_high_def = (bias <= 2.5)
        
        if is_high_exp and is_high_def:
            row_dict['🎯 戰術定位'] = "⭐ 雙劍合璧"
        elif is_high_exp and not is_high_def:
            row_dict['🎯 戰術定位'] = "🚀 動能突破"
        elif not is_high_exp and is_high_def:
            row_dict['🎯 戰術定位'] = "🐢 底部潛伏"
        else:
            row_dict['🎯 戰術定位'] = "👀 觀察雷達"
        
        # 戰術標籤 (備註)
        tags = []
        if trust_ratio >= 7.0:
            tags.append("🔴 結帳警戒(>7%)")
        elif 0.5 <= trust_ratio < 7.0 and consecutive_buy >= 2:
            tags.append("🟢 黃金起漲區")
            
        if consecutive_buy >= 3:
            tags.append(f"🔥 連買{consecutive_buy}天")
            
        row_dict['戰術標籤'] = " | ".join(tags) if tags else "一般"
        
        # 隱藏的總分 (僅用於預設排序，讓雙劍合璧排前面)
        row_dict['總分'] = exp_score + def_score
        
        final_results.append(row_dict)

    df_tech = pd.DataFrame(final_results)
    df_tech = df_tech.sort_values(by='總分', ascending=False)
    
    df_tech['投信買賣超'] = df_tech['投信買賣超'].astype(int)
    df_tech['外資買賣超'] = df_tech['外資買賣超'].astype(int)
    
    # 重新排列輸出的欄位 (移除舊的 MA20，讓畫面更乾淨)
    cols = ['代號', '名稱', '收盤價', '乖離率(%)', '投信買賣超', '外資買賣超', 
            '🔥 爆發力', '🛡️ 防禦力', '🎯 戰術定位', '動能比例(%)', '連買天數', '戰術標籤']
    
    return df_tech[cols]
