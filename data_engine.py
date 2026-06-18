import pandas as pd
import io
import streamlit as st

def parse_chip_csv(uploaded_file):
    """
    負責解析台灣證交所與櫃買中心的三大法人 CSV 檔案
    終極修復版：強制 cp950 解碼並忽略壞字，徹底解決亂碼與找不到表頭問題
    V23.1 更新：排除 0 開頭 ETF，精準抓取外陸資欄位
    """
    try:
        content = uploaded_file.read()
        
        # 1. 終極解碼防護網
        try:
            text = content.decode('cp950', errors='ignore')
        except Exception:
            text = content.decode('utf-8', errors='ignore')
            
        # 統一換行符號
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        lines = text.split('\n')
        
        # 2. 智慧尋找真實表頭
        header_idx = -1
        for i, line in enumerate(lines):
            clean_line = line.replace('"', '').replace(' ', '')
            if '代號' in clean_line or '代碼' in clean_line:
                header_idx = i
                break
                
        if header_idx == -1:
            st.error(f"檔案 {uploaded_file.name} 找不到包含「代號」的表頭行！")
            return None
            
        # 3. 讀取 CSV
        df = pd.read_csv(io.StringIO(text), skiprows=header_idx, engine='python', on_bad_lines='skip')
        
        # 4. 暴力清洗欄位名稱
        df.columns = [str(c).replace('"', '').replace(' ', '').replace('\n', '').strip() for c in df.columns]
        
        for col in df.columns:
            if '代號' in col or '代碼' in col:
                df.rename(columns={col: '代號'}, inplace=True)
                break
                
        for col in df.columns:
            if '名稱' in col:
                df.rename(columns={col: '名稱'}, inplace=True)
                break
        
        if '代號' not in df.columns:
            st.error(f"檔案 {uploaded_file.name} 欄位清洗後仍找不到「代號」！")
            return None
            
        # 5. 絕對鐵門：只保留 4 碼純數字的普通股 (排除 0 開頭的 ETF，如 0050)
        df['代號'] = df['代號'].astype(str).str.replace('=', '').str.replace('"', '').str.strip()
        df = df[df['代號'].str.match(r'^[1-9]\d{3}$')]
        
        # 6. 智慧尋標：尋找投信與外資買賣超欄位 (加入「外陸資」防呆)
        trust_col = next((c for c in df.columns if '投信' in c and '買賣超' in c), None)
        foreign_col = next((c for c in df.columns if ('外資' in c or '外陸資' in c) and '買賣超' in c and '不含' not in c), None)
        if not foreign_col: 
            foreign_col = next((c for c in df.columns if ('外資' in c or '外陸資' in c) and '買賣超' in c), None)
        
        # 7. 建立標準化 DataFrame 輸出
        df_clean = pd.DataFrame()
        df_clean['代號'] = df['代號']
        df_clean['名稱'] = df['名稱'] if '名稱' in df.columns else "未知"
        
        def to_sheets(series):
            return pd.to_numeric(series.astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0) / 1000
        
        df_clean['投信買賣超'] = to_sheets(df[trust_col]) if trust_col else 0.0
        df_clean['外資買賣超'] = to_sheets(df[foreign_col]) if foreign_col else 0.0
        
        return df_clean
        
    except Exception as e:
        st.error(f"解析檔案 {uploaded_file.name} 時發生未預期錯誤: {e}")
        return None
