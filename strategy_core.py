import pandas as pd
import concurrent.futures
import requests
from datetime import datetime, timedelta
import streamlit as st
import time
import yfinance as yf

def fetch_hybrid_data(code, today_trust_buy, token=""):
    """
    V24.2 雙引擎備援架構：yfinance (股價) + FinMind (籌碼)
    即使 FinMind 斷線，依然能保底輸出股價與 MA20，絕不漏接飆股！
    """
    close, ma20, bias = None, None, None
    trust_ratio = 0.0
    consecutive_buy = 0
    recent_20_buy = 0
    
    # ==========================================
    # 引擎一：yfinance 負責股價與 MA20 (極速、免費)
    # ==========================================
    for suffix in ['.TW', '.TWO']:
        try:
            tkr = yf.Ticker(f"{code}{suffix}")
            hist = tkr.history(period="2mo")
            if not hist.empty and len(hist) >= 20:
                close = float(hist['Close'].iloc[-1])
                ma20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
                bias = ((close - ma20) / ma20) * 100
                break  # 成功抓到就跳出迴圈
        except:
            continue
            
    # 如果連 yfinance 都抓不到股價 (可能是剛上市或下市)，才真的放棄這檔股票
    if close is None:
        return None, None, None, 0.0, 0

    # ==========================================
    # 引擎二：FinMind 負責進階籌碼與股本 (精準透視)
    # ==========================================
    try:
        token_str = f"&token={token}" if token else ""
        end_date = datetime.now()
        start_date = (end_date - timedelta(days=45)).strftime('%Y-%m-%d')
        today_str = end_date.strftime('%Y-%m-%d')
        
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
                            consecutive_buy += 1
                        else:
                            break
                            
                    # 解決時間差：如果最新資料不是今天，且 CSV 顯示今天有買超，則連買天數 +1
                    if latest_date != today_str and today_trust_buy > 0:
                        consecutive_buy += 1
                        
                    recent_20_buy = df_trust.head(20)['buy_sell'].sum()
                    if latest_date != today_str:
                        recent_20_buy += (today_trust_buy * 1000)

        # 2. 抓取發行股數 (計算動能比例)
        share_url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockShareholding&data_id={code}&start_date={start_date}{token_str}"
        res_share = requests.get(share_url, timeout=5 )
        if res_share.status_code == 200:
            share_data = res_share.json()
            if share_data.get('data'):
                df_share = pd.DataFrame(share_data['data'])
                latest_share_date = df_share['date'].max()
                total_shares = df_share[df_share['date'] == latest_share_date]['number_of_shares'].sum()
                
                if total_shares > 0:
                    trust_ratio = (recent_20_buy / total_shares) * 100

    except Exception as e:
        # 即使 FinMind 崩潰，我們依然有 yfinance 的股價保底！不會滅團！
        pass
        
    time.sleep(0.2) 
    
    return (
        round(close, 2), 
        round(ma20, 2), 
        round(bias, 2), 
        round(trust_ratio, 2), 
        consecutive_buy
    )

def calculate_scores(df, min_trust, max_bias, mode, finmind_token=""):
    """雙大腦評分邏輯核心"""
    
    df_filtered = df[df['投信買賣超'] >= min_trust].copy()
    if df_filtered.empty:
        return pd.DataFrame()

    st.info(f"⚡ 啟動雙引擎雷達：正在為 {len(df_filtered)} 檔標的進行深度 X 光掃描 (請稍候)...")
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_code = {executor.submit(fetch_hybrid_data, row['代號'], row['投信買賣超'], finmind_token): row for _, row in df_filtered.iterrows()}
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
                # 🌟 戰術標籤 (備註) 生成邏輯
                # ==========================================
                tags = []
                if trust_ratio >= 7.0:
                    tags.append("🔴 結帳警戒(>7%)")
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

    # 風險控管：剔除乖離率過高的危險標的
    df_tech = df_tech[df_tech['乖離率(%)'] <= max_bias].copy()
    if df_tech.empty:
        return pd.DataFrame()

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

    # 排序與整理最終戰報
    df_tech = df_tech.sort_values(by='總分', ascending=False)
    
    df_tech['投信買賣超'] = df_tech['投信買賣超'].astype(int)
    df_tech['外資買賣超'] = df_tech['外資買賣超'].astype(int)
    df_tech = df_tech.round(2)
    
    # 加入新欄位
    cols = ['代號', '名稱', '收盤價', 'MA20', '乖離率(%)', '投信買賣超', '外資買賣超', '動能比例(%)', '連買天數', '總分', '戰術標籤']
    
    return df_tech[cols]
