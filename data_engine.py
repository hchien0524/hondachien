import pandas as pd
import io
import re
import streamlit as st

def parse_single_csv(file_obj):
    """暴力解析單一 CSV 檔案 (自帶 X 光除錯雷達)"""
    content = file_obj.read()
    
    # 1. 破解編碼地雷 (加入 cp950 與 utf-16 備用)
    text = None
    for enc in ['utf-8-sig', 'big5', 'cp950', 'utf-16', 'utf-8']:
        try:
            text = content.decode(enc)
            break
        except:
            pass
            
    if not text:
        st.error(f"❌ 檔案 {file_obj.name} 解碼徹底失敗！請確認這是一般的 CSV 檔。")
        return pd.DataFrame()
            
    # 2. 破解上櫃「廢話標題」地雷
    lines = text.split('\n')
    header_idx = 0
    for i, line in enumerate(lines[:15]):
        if '代號' in line or '代碼' in line or '名稱' in line or '證券代號' in line:
            header_idx = i
            break
            
    df = pd.read_csv(io.StringIO(text), skiprows=header_idx, dtype=str, on_bad_lines='skip')
    df.columns = [str(c).replace('"', '').replace(' ', '').strip() for c in df.columns]
    
    col_code = next((c for c in df.columns if '代號' in c or '代碼' in c), None)
    col_name = next((c for c in df.columns if '名稱' in c or '股名' in c), None)
    
    if not col_code:
        st.warning(f"⚠️ 【X光雷達】檔案 {file_obj.name} 找不到代號欄位！\n目前抓到的欄位有：{df.columns.tolist()}")
        return pd.DataFrame()
        
    # 紀錄過濾前的代號，用來除錯
    raw_codes = df[col_code].dropna().head(10).tolist()
        
    # 🔥 核彈級脫殼：清除代號裡面的 ="3293" 或 "3293" 或空白
    df[col_code] = df[col_code].astype(str).str.replace(r'["= ]', '', regex=True).str.strip()
    
    # 絕對鐵門：只保留 4 碼純血普通股
    df_filtered = df[df[col_code].str.match(r'^\d{4}$', na=False)]
    
    if df_filtered.empty:
        st.warning(f"⚠️ 【X光雷達】檔案 {file_obj.name} 過濾 4 碼普通股後全軍覆沒！\n原始代號長這樣：{raw_codes}")
        return pd.DataFrame()
        
    df = df_filtered
    
    # 尋找投信與外資
    col_it = next((c for c in df.columns if '投信' in c and '買賣超' in c), None)
    col_fi = None
    for c in df.columns:
        if '外資及陸資-買賣超' in c or '外陸資買賣超' in c:
            col_fi = c
            break
    if not col_fi:
        col_fi = next((c for c in df.columns if '外資' in c and '買賣超' in c), None)
        
    res = pd.DataFrame()
    res['代號'] = df[col_code]
    res['名稱'] = df[col_name] if col_name else "未知"
    
    def clean_num(x):
        if pd.isna(x): return 0
        s = str(x).replace(',', '').replace('"', '').strip()
        try: return float(s)
        except: return 0
        
    res['投信買賣超'] = df[col_it].apply(clean_num) if col_it else 0
    res['外資買賣超'] = df[col_fi].apply(clean_num) if col_fi else 0
    
    if res['投信買賣超'].abs().max() > 10000 or res['外資買賣超'].abs().max() > 10000:
        res['投信買賣超'] = res['投信買賣超'] / 1000
        res['外資買賣超'] = res['外資買賣超'] / 1000
        
    return res

def clean_csv_data(uploaded_files):
    dfs = []
    for f in uploaded_files:
        f.seek(0)
        df = parse_single_csv(f)
        if not df.empty:
            dfs.append(df)
            
    if not dfs:
        return pd.DataFrame()
    
    final_df = pd.concat(dfs, ignore_index=True)
    final_df = final_df.drop_duplicates(subset=['代號'], keep='last')
    return final_df
