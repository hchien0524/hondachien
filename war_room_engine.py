import pandas as pd
import numpy as np
import yfinance as yf
import requests
import time
import streamlit as st

class WarRoomEngine:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        
    def _fetch_openapi_data(self):
        data_lake = {}
        try:
            twse_price = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", headers=self.headers, timeout=10 ).json()
            twse_pe = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL", headers=self.headers, timeout=10 ).json()
            for item in twse_price:
                code = item.get('Code')
                if code:
                    data_lake[code] = {'Market': 'TWSE', 'Close': pd.to_numeric(item.get('ClosingPrice') or item.get('Close'), errors='coerce')}
            for item in twse_pe:
                code = item.get('Code')
                if code and code in data_lake:
                    data_lake[code]['PE'] = pd.to_numeric(item.get('PEratio') or item.get('PERatio') or item.get('PeRatio'), errors='coerce')

            tpex_price = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes", headers=self.headers, timeout=10 ).json()
            tpex_pe = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis", headers=self.headers, timeout=10 ).json()
            for item in tpex_price:
                code = item.get('SecuritiesCompanyCode') or item.get('Code')
                if code:
                    if code not in data_lake: data_lake[code] = {'Market': 'TPEx'}
                    data_lake[code]['Close'] = pd.to_numeric(item.get('Close') or item.get('ClosingPrice'), errors='coerce')
            for item in tpex_pe:
                code = item.get('SecuritiesCompanyCode') or item.get('Code')
                if code and code in data_lake:
                    data_lake[code]['PE'] = pd.to_numeric(item.get('PERatio') or item.get('PeRatio') or item.get('PEratio'), errors='coerce')
        except Exception as e:
            print(f"OpenAPI Error: {e}")
        return data_lake

    def process_chips(self, df_list):
        if not df_list: return pd.DataFrame()

        chip_data = {}
        for i, df in enumerate(df_list):
            foreign_col = next((c for c in df.columns if ('外陸資' in c or '外資及陸資' in c) and '買賣超' in c), None)
            trust_col = next((c for c in df.columns if '投信' in c and '買賣超' in c), None)
            code_col = next((c for c in df.columns if '代號' in c), None)
            name_col = next((c for c in df.columns if '名稱' in c), None)
            
            if not all([foreign_col, trust_col, code_col, name_col]): continue
                
            for _, row in df.iterrows():
                code = str(row[code_col]).replace('=', '').replace('"', '').strip()
                name = str(row[name_col]).strip()
                
                if len(code) != 4 or not code.isdigit() or code.startswith('0'): continue
                
                try:
                    f_buy = float(str(row[foreign_col]).replace(',', ''))
                    t_buy = float(str(row[trust_col]).replace(',', ''))
                    net_buy = (f_buy + t_buy) / 1000 
                except: continue
                    
                if code not in chip_data:
                    chip_data[code] = {'代號': code, '名稱': name, '買超天數': 0, '總買超張數': 0, '近期買超': 0, '早期買超': 0}
                
                if net_buy > 0: chip_data[code]['買超天數'] += 1
                chip_data[code]['總買超張數'] += net_buy
                
                if i >= len(df_list) - 2: chip_data[code]['近期買超'] += net_buy
                else: chip_data[code]['早期買超'] += net_buy

        candidates = [v for v in chip_data.values() if v['買超天數'] >= 2 or v['總買超張數'] > 300]
        if not candidates: return pd.DataFrame()

        data_lake = self._fetch_openapi_data()
        results, debug_logs = [], []
        progress_bar, status_text = st.progress(0), st.empty()
        
        total_candidates = len(candidates)
        for idx, item in enumerate(candidates):
            code, name = item['代號'], item['名稱']
            status_text.text(f"正在進行 X 光掃描: {code} {name} ({idx+1}/{total_candidates})")
            progress_bar.progress((idx + 1) / total_candidates)
            
            market_info = data_lake.get(code, {})
            pe_ratio = market_info.get('PE', np.nan)
            market_type = market_info.get('Market', 'TWSE') 
            
            hist = pd.DataFrame()
            time.sleep(0.1) 
            
            yf_code = f"{code}.TW" if market_type == 'TWSE' else f"{code}.TWO"
            try:
                ticker = yf.Ticker(yf_code)
                hist = ticker.history(period="80d")
                # 🛡️ 雙重 PE 備援
                if pd.isna(pe_ratio):
                    pe_ratio = ticker.info.get('trailingPE', np.nan)
            except: pass
                
            if hist.empty or len(hist) < 60:
                time.sleep(0.1)
                fallback_code = f"{code}.TWO" if market_type == 'TWSE' else f"{code}.TW"
                try:
                    ticker = yf.Ticker(fallback_code)
                    hist = ticker.history(period="80d")
                    if pd.isna(pe_ratio):
                        pe_ratio = ticker.info.get('trailingPE', np.nan)
                except: pass
            
            if hist.empty:
                debug_logs.append({'代號': code, '名稱': name, '淘汰原因': 'yfinance 完全抓無資料'})
                continue
            if len(hist) < 60:
                debug_logs.append({'代號': code, '名稱': name, '淘汰原因': f'K線資料不足60天'})
                continue
                
            try:
                close = hist['Close'].iloc[-1]
                ma10 = hist['Close'].rolling(window=10).mean().iloc[-1]
                ma60 = hist['Close'].rolling(window=60).mean().iloc[-1]
                vol_5d = hist['Volume'].iloc[-5:].mean() / 1000
                high_20d = hist['High'].iloc[-21:-1].max()
                
                bias_10 = (close - ma10) / ma10
                bias_60 = (close - ma60) / ma60
                
                early_avg = item['早期買超'] / max(1, (len(df_list) - 2))
                recent_avg = item['近期買超'] / 2
                ignition = recent_avg / early_avg if early_avg > 0 else (3.0 if recent_avg > 500 else 0)
                
                tags = []
                has_core_tag = False # 🛡️ 核心標籤判定機制
                
                if pd.notna(pe_ratio) and 0 < pe_ratio < 15:
                    tags.append("[🛡️ 價值防禦]")
                    has_core_tag = True
                if abs(bias_60) <= 0.05:
                    tags.append("[📉 底部打底]")
                    has_core_tag = True
                if ignition >= 3.0 and bias_10 > -0.02:
                    tags.append("[🔥 動能爆發]")
                    has_core_tag = True
                    
                if close < high_20d:
                    tags.append("[🛑 未創高]")
                if vol_5d > 800:
                    tags.append("[🌊 流動性佳]")
                    
                # 必須具備至少一個核心標籤才算及格
                if has_core_tag:
                    item['收盤價'] = round(close, 2)
                    item['本益比'] = round(pe_ratio, 2) if pd.notna(pe_ratio) else "N/A"
                    item['季線乖離'] = f"{bias_60*100:.1f}%"
                    item['點火倍數'] = round(ignition, 1)
                    item['戰略標籤'] = " ".join(tags)
                    results.append(item)
                else:
                    pe_str = f"{pe_ratio:.1f}" if pd.notna(pe_ratio) else "N/A"
                    reason = f"無核心標籤 (PE:{pe_str}, 季乖離:{bias_60*100:.1f}%, 點火:{ignition:.1f}, 均量:{vol_5d:.0f}張)"
                    debug_logs.append({'代號': code, '名稱': name, '淘汰原因': reason})
                    
            except Exception as e:
                debug_logs.append({'代號': code, '名稱': name, '淘汰原因': f'計算錯誤: {str(e)}'})
                continue
                
        progress_bar.empty()
        status_text.empty()
        
        if debug_logs:
            with st.expander(f"🛠️ 系統診斷報告 (共 {len(debug_logs)} 檔未達標)", expanded=True):
                st.dataframe(pd.DataFrame(debug_logs), use_container_width=True)
        
        if not results:
            return pd.DataFrame()
            
        df_result = pd.DataFrame(results)
        cols = ['代號', '名稱', '收盤價', '本益比', '季線乖離', '買超天數', '總買超張數', '點火倍數', '戰略標籤']
        return df_result[cols].sort_values(by='總買超張數', ascending=False)
