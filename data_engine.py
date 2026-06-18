import pandas as pd
import io
import streamlit as st

def parse_chip_csv(uploaded_file):
    """
    負責解析台灣證交所與櫃買中心的三大法人 CSV 檔案
    具備 Big5/UTF-8 自動解碼、垃圾表頭過濾、4碼普通股純化功能
    """
    try:
        content = uploaded_file.read()
        
        # 1. 終極解碼防護網
        try:
            text = content.decode('big5')
        except UnicodeDecodeError:
            text = content.decode('utf-8', errors='replace')
            
        # 統一換行符號，避免 \r\n 造成的解析錯誤
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        lines = text.split('\n')
        
        # 2. 智慧尋找真實表頭
        header_idx = -1
        for i, line in enumerate(lines):
            # 移除引號與空白，方便精準比對
            clean_line = line.replace('"', '').replace(' ', '')
            if '代號' in clean_line or '代碼' in clean_line:
                header_idx = i
                break
                
        if header_idx == -1:
            st.error(f"檔案 {uploaded_file.name} 找不到包含「代號」的表頭行！")
            return None
            
        # 3. 讀取 CSV (關鍵修復：使用 python engine 並略過結尾的垃圾說明行)
        df = pd.read_csv(io.StringIO(text), skiprows=header_idx, engine='python', on_bad_lines='skip')
        
        # 4. 暴力清洗欄位名稱
        # 移除所有引號、空白、換行符號
        df.columns = [str(c).replace('"', '').replace(' ', '').replace('\n', '').strip() for c in df.columns]
        
        # 尋找並重新命名代號欄位
        for col in df.columns:
            if '代號' in col or '代碼' in col:
                df.rename(columns={col: '代號'}, inplace=True)
                break
                
        if '代號' not in df.columns:
            # 如果還是找不到，印出目前抓到的欄位讓總司令除錯
            st.error(f"檔案 {uploaded_file.name} 欄位清洗後仍找不到「代號」！目前抓到的欄位有：{list(df.columns)}")
            return None
            
        # 尋找並重新命名名稱欄位
        for col in df.columns:
            if '名稱' in col:
                df.rename(columns={col: '名稱'}, inplace=True)
                break
        
        # 5. 絕對鐵門：只保留 4 碼純數字的普通股
        # 關鍵修復：移除官方有時候會加的 '=' (例如 ="2330")
        df['代號'] = df['代號'].astype(str).str.replace('=', '').str.replace('"', '').str.strip()
        df = df[df['代號'].str.match(r'^\d{4}$')]
        
        # 6. 智慧尋標：尋找投信與外資買賣超欄位
        trust_col = next((c for c in df.columns if '投信' in c and '買賣超' in c), None)
        foreign_col = next((c for c in df.columns if '外資' in c and '買賣超' in c and '不含' not in c), None)
        if not foreign_col: 
            foreign_col = next((c for c in df.columns if '外資' in c and '買賣超' in c), None)
        
        # 7. 建立標準化 DataFrame 輸出
        df_clean = pd.DataFrame()
        df_clean['代號'] = df['代號']
        df_clean['名稱'] = df['名稱'] if '名稱' in df.columns else "未知"
        
        # 轉換數字並換算成「張」 (除以 1000)
        def to_sheets(series):
            return pd.to_numeric(series.astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0) / 1000
        
        df_clean['投信買賣超'] = to_sheets(df[trust_col]) if trust_col else 0.0
        df_clean['外資買賣超'] = to_sheets(df[foreign_col]) if foreign_col else 0.0
        
        return df_clean
        
    except Exception as e:
        st.error(f"解析檔案 {uploaded_file.name} 時發生未預期錯誤: {e}")
        return None
