import pandas as pd
import yfinance as yf
import numpy as np

def calculate_scores(df_chips, min_trust, max_bias):
    """V21.1 混血大腦：融合籌碼、技術、溫和放量與基本面加分"""
    df_filtered = df_chips[df_chips['投信買賣超'] >= min_trust].copy()
    if df_filtered.empty:
        return pd.DataFrame()

    results = []
    
    for index, row in df_filtered.iterrows():
        code = row['代號']
        ticker = f"{code}.TW"
        
        try:
            stock = yf.Ticker(ticker)
            # 抓取1個月資料即可計算 MA20 與 MA5_Vol，大幅提升掃描速度
            hist = stock.history(period="1mo") 
            if hist.empty:
                ticker = f"{code}.TWO"
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1mo")
                
            if len(hist) < 20:
                continue
                
            # 價格與均線計算
            close_price = hist['Close'].iloc[-1]
            ma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
            bias_20 = ((close_price - ma20) / ma20) * 100
            
            # 🛡️ 絕對防守線 1：乖離率過大直接剔除 (不追高)
            if bias_20 > max_bias:
                continue
                
            # 量能計算 (yfinance 台股成交量通常是股數，除以1000變張數)
            vol_today = hist['Volume'].iloc[-1] / 1000
            ma5_vol = hist['Volume'].rolling(window=5).mean().iloc[-1] / 1000
            
            # 🛡️ 絕對防守線 2：流動性陷阱剔除 (單日成交量 < 300張，直接刷掉，不買死水股)
            if vol_today < 300:
                continue
                
            # ==========================================
            # 多維度評分與標籤系統 (滿分 100)
            # ==========================================
            score = 0
            tags = []
            
            # 1. 籌碼力 (滿分 40)
            chip_score = 0
            if row['投信買賣超'] > 500: 
                chip_score += 30
                tags.append("重金鎖碼")
            elif row['投信買賣超'] >= 100: 
                chip_score += 20
            
            if row['外資買賣超'] > 0: 
                chip_score += 10
                tags.append("土洋齊買")
            score += chip_score
            
            # 2. 技術力 (滿分 30)
            tech_score = 0
            if 0 < bias_20 <= 5: 
                tech_score += 30
                tags.append("低乖離")
            elif 5 < bias_20 <= 10: 
                tech_score += 15
            score += tech_score
            
            # 3. 動能力 (滿分 15)
            vol_score = 0
            if vol_today > ma5_vol * 1.1: # 今天量大於5日均量10%
                vol_score += 15
                tags.append("溫和放量")
            score += vol_score
            
            # 4. 基本力 (加分項，滿分 15)
            # 使用 try-except 快速抓取，抓不到就算了，不卡死系統效能
            fund_score = 0
            try:
                info = stock.info
                rev_growth = info.get('revenueGrowth', 0)
                gross_margin = info.get('grossMargins', 0)
                
                if rev_growth and rev_growth > 0.1: # 營收成長 > 10%
                    fund_score += 10
                    tags.append("營收雙位數成長")
                if gross_margin and gross_margin > 0.2: # 毛利率 > 20%
                    fund_score += 5
                    tags.append("高毛利")
            except:
                pass # 抓不到基本面不扣分，保護轉機股
            score += fund_score
            
            results.append({
                '代號': code,
                '名稱': row['名稱'],
                '收盤價': round(close_price, 2),
                '總分': score,
                '籌碼力': chip_score,
                '技術力': tech_score,
                '動能力': vol_score,
                '基本力': fund_score,
                '投信買賣超': row['投信買賣超'],
                '外資買賣超': row['外資買賣超'],
                '乖離率(%)': round(bias_20, 2),
                '今日量(張)': round(vol_today, 0),
                '戰術標籤': " | ".join(tags)
            })
            
        except Exception as e:
            continue
            
    if not results:
        return pd.DataFrame()
        
    df_results = pd.DataFrame(results)
    return df_results.sort_values('總分', ascending=False)
