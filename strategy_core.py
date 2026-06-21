import pandas as pd
import yfinance as yf
import streamlit as st
import concurrent.futures
import requests
from datetime import datetime, timedelta

def fetch_finmind_data(code, trust_buy_today, token=""):
    """抓取 FinMind 籌碼數據，計算動能比例與連買天數"""
    momentum_pct = 0.0
    continuous_days = 0
    
    try:
        end_date = datetime.now()
        start_date = (end_date - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        headers = {'Authorization': f'Bearer {token}'} if token else {}
        
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
                            
        info_url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInfo&data_id={code}"
        res_info = requests.get(info_url, headers=headers, timeout=5 )
        if res_info.status_code == 200:
            info_data = res_info.json()
            if len(info_data.get('data', [])) > 0:
                shares_outstanding = info_data['data'][0].get('IssuedShares', 0)
                if shares_outstanding > 0:
                    momentum_pct = round((trust_buy_today * 1000 / shares_outstanding) * 100, 2)
                    
    except Exception:
        pass
        
    return momentum_pct, continuous_days

def fetch_price_and_ma(code):
    """抓取收盤價與 MA20，並回傳正確的後綴 (.TW 或 .TWO)"""
    for suffix in ['.TW', '.TWO']:
        try:
            tkr = yf.Ticker(f"{code}{suffix}")
            hist = tkr.history(period="2mo")
            if not hist.empty and len(hist) >= 20:
                close = float(hist['Close'].iloc[-1])
                ma20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
                bias = ((close - ma20) / ma20) * 100
                return round(close, 2), round(ma20, 2), round(bias, 2), suffix
        except:
            continue
    return None, None, None, None

def process_stock(row, token):
    """單檔股票處理流 (修復上櫃 Bug 版)"""
    code = row['代號']
    trust_buy = row['投信買賣超']
    
    # 1. 先抓價格，同時取得這檔股票是上市還是上櫃 (suffix)
    close, ma20, bias, suffix = fetch_price_and_ma(code)
    if close is None:
        return None
        
    # 2. 抓取 FinMind 數據
    mom_pct, days = fetch_finmind_data(code, trust_buy, token)
    
    # 3. 完美的 yfinance 股本備援機制
    if mom_pct == 0 and suffix is not None:
        try:
            # 直接使用剛剛確認過正確的後綴 (.TW 或 .TWO) 去查股本，絕不報錯！
            tkr = yf.Ticker(f"{code}{suffix}")
            shares = tkr.info.get('sharesOutstanding', 0)
            if shares > 0:
                mom_pct = round((trust_buy * 1000 / shares) * 100, 2)
        except:
            pass

    row_dict = row.to_dict()
    row_dict['收盤價'] = close
    row_dict['MA20'] = ma20
    row_dict['乖離率(%)'] = bias
    row_dict['動能比例(%)'] = mom_pct
    row_dict['連買天數'] = days
    return row_dict

def calculate_scores(df, min_trust, max_bias, max_price, token=""):
    """終極單一總分演算引擎"""
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

    # 1. 乖離率濾網
    df_res = df_res[df_res['乖離率(%)'] <= max_bias]
    # 2. 股價上限濾網
    df_res = df_res[df_res['收盤價'] <= max_price]
    
    # 3. 外資倒貨否決權
    if '外資買賣超' not in df_res.columns:
        df_res['外資買賣超'] = 0
    dump_condition = (df_res['外資買賣超'] < 0) & (df_res['外資買賣超'].abs() > df_res['投信買賣超'] * 3)
    df_res = df_res[~dump_condition]

    if df_res.empty: return pd.DataFrame()

    # 🏆 總分演算
    base_score = (df_res['投信買賣超'] / 100 * 0.6) + (df_res['外資買賣超'] / 100 * 0.4)
    mom_score = df_res['動能比例(%)'] * 50
    def_score = (max_bias - df_res['乖離率(%)']) * 10

    df_res['🏆 總分'] = base_score + mom_score + def_score
    
    df_res = df_res.sort_values(by='🏆 總分', ascending=False).round(2)
    df_res['投信買賣超'] = df_res['投信買賣超'].astype(int)
    df_res['外資買賣超'] = df_res['外資買賣超'].astype(int)
    df_res['連買天數'] = df_res['連買天數'].astype(int)

    cols = ['代號', '名稱', '收盤價', '乖離率(%)', '投信買賣超', '外資買賣超', '動能比例(%)', '連買天數', '🏆 總分']
    return df_res[cols]
