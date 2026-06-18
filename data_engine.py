import pandas as pd
import io
import re
import streamlit as st

def parse_chip_csv(uploaded_file):
    """
    負責解析台灣證交所與櫃買中心的三大法人 CSV 檔案
    具備 Big5/UTF-8 自動解碼、垃圾表頭過濾、4碼普通股純化功能
    """
    try:
        content = uploaded_file.read()
        
        # 1. 終極解碼防護網 (先試 Big5，再試 UTF-8)
        try:
            text = content.decode('big5')
        except UnicodeDecodeError:
            text = content.decode('utf-8', errors='replace')
        
        lines = text.split('\n')
        
        # 2. 智慧尋找真實表頭 (跳過官方的垃圾說明文字)
        header_idx = 0
        for i, line in enumerate(lines):
            if '代號' in line or '代碼' in line:
                header_idx = i
                break
                
        # 3. 讀取 CSV
        df = pd.read_csv(io.StringIO(text), skiprows=header_idx)
        
        # 4. 清洗欄位名稱 (去除隱形空白與換行符號)
        df.columns = df.columns.str.strip().str.replace('\r', '').str.replace('\n', '')
        
        # 確保有代號欄位
        if '代號' not in df.columns:
            for col in df.columns:
                if '代號' in col or '代碼' in col:
                    df.rename(columns={col: '代號'}, inplace=True)
                    break
        
        if '代號' not in df.columns:
            st.error(f"檔案 {uploaded_file.name} 找不到「代號」欄位！")
            return None
            
        # 5. 絕對鐵門：只保留 4 碼純數字的普通股 (過濾權證、ETF、牛熊證)
        df['代號'] = df['代號'].astype(str).str.replace('"', '').str.strip()
        df = df[df['代號'].str.match(r'^\d{4}$')]
        
        # 6. 智慧尋標：尋找投信與外資買賣超欄位
        trust_col = next((c for c in df.columns if '投信' in c and '買賣超' in c), None)
        # 外資欄位優先找「外資及陸資-買賣超」，避開只算自營商的
        foreign_col = next((c for c in df.columns if '外資' in c and '買賣超' in c and '不含' not in c), None)
        if not foreign_col: 
            foreign_col = next((c for c in df.columns if '外資' in c and '買賣超' in c), None)
        
        # 7. 建立標準化 DataFrame 輸出
        df_clean = pd.DataFrame()
        df_clean['代號'] = df['代號']
        df_clean['名稱'] = df['名稱'].astype(str).str.replace('"', '').str.strip() if '名稱' in df.columns else "未知"
        
        # 轉換數字並換算成「張」 (除以 1000)
        def to_sheets(series):
            return pd.to_numeric(series.astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0) / 1000
        
        df_clean['投信買賣超'] = to_sheets(df[trust_col]) if trust_col else 0.0
        df_clean['外資買賣超'] = to_sheets(df[foreign_col]) if foreign_col else 0.0
        
        return df_clean
        
    except Exception as e:
        st.error(f"解析檔案 {uploaded_file.name} 時發生未預期錯誤: {e}")
        return None
