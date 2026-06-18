import pandas as pd
import io
import re

def parse_single_csv(file_obj):
    """暴力解析單一 CSV 檔案 (支援上市與上櫃的各種奇葩格式)"""
    content = file_obj.read()
    
    # 1. 破解編碼地雷
    try: text = content.decode('utf-8-sig')
    except:
        try: text = content.decode('big5', errors='ignore')
        except: text = content.decode('utf-8', errors='ignore')
            
    # 2. 破解上櫃「廢話標題」地雷
    lines = text.split('\n')
    header_idx = 0
    for i, line in enumerate(lines[:15]):
        if '代號' in line or '代碼' in line or '名稱' in line:
            header_idx = i
            break
            
    df = pd.read_csv(io.StringIO(text), skiprows=header_idx, dtype=str, on_bad_lines='skip')
    df.columns = [str(c).replace('"', '').replace(' ', '').strip() for c in df.columns]
    
    col_code = next((c for c in df.columns if '代號' in c or '代碼' in c), None)
    col_name = next((c for c in df.columns if '名稱' in c or '股名' in c), None)
    
    # 尋找投信與外資 (精準鎖定總計欄位)
    col_it = next((c for c in df.columns if '投信' in c and '買賣超' in c), None)
    col_fi = None
    for c in df.columns:
        if '外資及陸資-買賣超' in c or '外陸資買賣超' in c:
            col_fi = c
            break
    if not col_fi:
        col_fi = next((c for c in df.columns if '外資' in c and '買賣超' in c), None)
        
    if not col_code:
        return pd.DataFrame()
        
    # 🔥 核彈級脫殼：清除代號裡面的 ="3293" 或 "3293" 或空白
    df[col_code] = df[col_code].astype(str).str.replace(r'["= ]', '', regex=True).str.strip()
    
    # 絕對鐵門：只保留 4 碼純血普通股
    df = df[df[col_code].str.match(r'^\d{4}$', na=False)]
    
    res = pd.DataFrame()
    res['代號'] = df[col_code]
    res['名稱'] = df[col_name] if col_name else "未知"
    
    # 數字清洗與轉換
    def clean_num(x):
        if pd.isna(x): return 0
        s = str(x).replace(',', '').replace('"', '').strip()
        try: return float(s)
        except: return 0
        
    res['投信買賣超'] = df[col_it].apply(clean_num) if col_it else 0
    res['外資買賣超'] = df[col_fi].apply(clean_num) if col_fi else 0
    
    # 單位校正 (股轉張)
    if res['投信買賣超'].abs().max() > 10000 or res['外資買賣超'].abs().max() > 10000:
        res['投信買賣超'] = res['投信買賣超'] / 1000
        res['外資買賣超'] = res['外資買賣超'] / 1000
        
    return res

def clean_csv_data(uploaded_files):
    """處理多個上傳的檔案並合併"""
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
