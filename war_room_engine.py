import pandas as pd
import numpy as np
import yfinance as yf
import requests
import time
import streamlit as st

class WarRoomEngine:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
    def _fetch_openapi_data(self):
        """建立全局資料湖：一次性抓取上市櫃本益比與收盤價"""
        data_lake = {}
        try:
            twse_price = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", headers=self.headers, timeout=10 ).json()
            twse_pe = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL", headers=self.headers, timeout=10 ).json()
            
            for item in twse_price:
                code = item.get('Code')
                if not code: continue
                if code not in data_lake: data_lake[code] = {'Market': 'TWSE'}
                data_lake[code]['Close'] = pd.to_numeric(item.get('ClosingPrice') or item.get('Close'), errors='coerce')
                
            for item in twse_pe:
                code = item.get('Code')
                if not code: continue
                if code in data_lake:
                    data_lake[code]['PE'] = pd.to_numeric(item.get('PEratio') or item.get('PERatio') or item.get('PeRatio'), errors='coerce')

            tpex_price = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes", headers=self.headers, timeout=10 ).json()
            tpex_pe = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis", headers=self.headers, timeout=10 ).json()
            
            for item in tpex_price:
                code = item.get('SecuritiesCompanyCode') or item.get('Code')
                if not code: continue
                if code not in data_lake: data_lake[code] = {'Market': 'TPEx'}
                data_lake[code]['Close'] = pd.to_numeric(item.get('Close') or item.get('ClosingPrice'), errors='coerce')
                
            for item in tpex_pe:
                code = item.get('SecuritiesCompanyCode') or item.get('Code')
                if not code: continue
                if code in data_lake:
                    data_lake[code]['PE'] = pd.to_numeric(item.get('PERatio') or item.get('PeRatio') or item.get('PEratio'), errors='coerce')
        except Exception as e:
            print(f"OpenAPI 獲取失敗: {e}")
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

        # 漏斗：買超 >= 2 天 或 總買超 > 300 張
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
