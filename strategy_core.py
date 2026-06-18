import pandas as pd
import yfinance as yf
import numpy as np

def calculate_scores(df_chips, min_trust, max_bias, strategy_mode="短波段突擊 (V21.1)"):
    """雙大腦核心：支援短波段動能與大波段翻倍邏輯"""
    df_filtered = df_chips[df_chips['投信買賣超'] >= min_trust].copy()
    if df_filtered.empty:
        return pd.DataFrame()

    results = []
    
    for index, row in df_filtered.iterrows():
        code = row['代號']
        ticker = f"{code}.TW"
        
        try:
            stock = yf.Ticker(ticker)
            
            # ==========================================
            # 🧠 大腦 A：短波段突擊模式 (V21.1 原有邏輯)
            # ==========================================
            if strategy_mode == "短波段突擊 (V21.1)":
                hist = stock.history(period="1mo") 
                if hist.empty:
                    ticker = f"{code}.TWO"
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period="1mo")
                    
                if len(hist) < 20: continue
                    
                close_price = hist['Close'].iloc[-1]
                ma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
                bias_20 = ((close_price - ma20) / ma20) * 100
                
                if bias_20 > max_bias: continue
                    
                vol_today = hist['Volume'].iloc[-1] / 1000
                ma5_vol = hist['Volume'].rolling(window=5).mean().iloc[-1] / 1000
                
                if vol_today < 300: continue
                    
                score = 0
                tags = []
                
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
                
                tech_score = 0
                if 0 < bias_20 <= 5: 
                    tech_score += 30
                    tags.append("低乖離")
                elif 5 < bias_20 <= 10: 
                    tech_score += 15
                score += tech_score
                
                vol_score = 0
                if vol_today > ma5_vol * 1.1:
                    vol_score += 15
                    tags.append("溫和放量")
                score += vol_score
                
                fund_score = 0
                try:
                    info = stock.info
                    rev_growth = info.get('revenueGrowth', 0)
                    gross_margin = info.get('grossMargins', 0)
                    if rev_growth and rev_growth > 0.1: 
                        fund_score += 10
                        tags.append("營收雙位數成長")
                    if gross_margin and gross_margin > 0.2: 
                        fund_score += 5
                        tags.append("高毛利")
                except: pass
                score += fund_score
                
                results.append({
                    '代號': code, '名稱': row['名稱'], '收盤價': round(close_price, 2),
                    '總分': score, '籌碼力': chip_score, '技術力': tech_score,
                    '動能力': vol_score, '基本力': fund_score,
                    '投信買賣超': row['投信買賣超'], '外資買賣超': row['外資買賣超'],
                    '乖離率(%)': round(bias_20, 2), '今日量(張)': round(vol_today, 0),
                    '戰術標籤': " | ".join(tags)
                })

            # ==========================================
            # 🧠 大腦 B：大波段翻倍模式 (全新長線邏輯)
            # ==========================================
            else:
                hist = stock.history(period="6mo") 
                if hist.empty:
                    ticker = f"{code}.TWO"
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period="6mo")
                    
                if len(hist) < 60: continue # 必須要有季線資料
                    
                close_price = hist['Close'].iloc[-1]
                ma60 = hist['Close'].rolling(window=60).mean().iloc[-1]
                low_6mo = hist['Low'].min()
                
                # 🛡️ 絕對防守線：必須站上季線 (MA60生命線)
                if close_price < ma60: continue
                    
                # 計算底部漲幅 (距離半年最低點漲了多少)
                rise_from_bottom = ((close_price - low_6mo) / low_6mo) * 100
                
                score = 0
                tags = []
                
                # 1. 底部基期分數 (滿分 40) - 越接近底部越高分
                base_score = 0
                if rise_from_bottom <= 15:
                    base_score += 40
                    tags.append("大底剛突破")
                elif rise_from_bottom <= 30:
                    base_score += 25
                    tags.append("底部起漲")
                elif rise_from_bottom > 50:
                    continue # 漲超過50%不追高，直接剔除！
                score += base_score
                
                # 2. 基本面護城河 (滿分 40) - 長線極度看重
                fund_score = 0
                try:
                    info = stock.info
                    rev_growth = info.get('revenueGrowth', 0)
                    gross_margin = info.get('grossMargins', 0)
                    
                    if rev_growth and rev_growth > 0.15: 
                        fund_score += 20
                        tags.append("營收大爆發")
                    elif rev_growth and rev_growth > 0:
                        fund_score += 10
                        
                    if gross_margin and gross_margin > 0.25: 
                        fund_score += 20
                        tags.append("極高毛利護城河")
                    elif gross_margin and gross_margin > 0.15:
                        fund_score += 10
                except: pass
                score += fund_score
                
                # 3. 籌碼安定度 (滿分 20)
                chip_score = 0
                if row['投信買賣超'] > 0 and row['外資買賣超'] > 0:
                    chip_score += 20
                    tags.append("長線土洋共識")
                elif row['投信買賣超'] > 300:
                    chip_score += 10
                score += chip_score
                
                results.append({
                    '代號': code, '名稱': row['名稱'], '收盤價': round(close_price, 2),
                    '總分': score, '基期力': base_score, '基本力': fund_score,
                    '籌碼力': chip_score, '底部漲幅(%)': round(rise_from_bottom, 2),
                    '投信買賣超': row['投信買賣超'], '外資買賣超': row['外資買賣超'],
                    '戰術標籤': " | ".join(tags)
                })
                
        except Exception as e:
            continue
            
    if not results:
        return pd.DataFrame()
        
    df_results = pd.DataFrame(results)
    return df_results.sort_values('總分', ascending=False)
