import pandas as pd
import io

def clean_csv_data(uploaded_files):
    """負責讀取 CSV、自動跳過廢話標題、清洗亂碼"""
    dfs = []
    for f in uploaded_files:
        try:
            content = f.read().decode('utf-8', errors='replace')
            lines = content.split('\n')
            
            # 智慧尋標：自動往下找，直到發現包含 '代號' 的那一行當作標題
            header_idx = 0
            for i, line in enumerate(lines):
                if '代號' in line or '代碼' in line:
                    header_idx = i
                    break
            
            # 重新讀取，精準跳過前面的廢話
            df = pd.read_csv(io.StringIO(content), skiprows=header_idx, dtype=str)
            dfs.append(df)
        except Exception as e:
            continue
            
    if not dfs:
        return pd.DataFrame()
        
    raw_df = pd.concat(dfs, ignore_index=True)
    
    # 找出真正的欄位名稱
    code_col = next((c for c in raw_df.columns if '代號' in c or '代碼' in c), None)
    name_col = next((c for c in raw_df.columns if '名稱' in c), None)
    
    # 終極盲抓投信與外資 (防禦上櫃 CSV 的奇怪命名)
    trust_col = next((c for c in raw_df.columns if '投信' in c and ('買賣超' in c or '淨買' in c)), None)
    if not trust_col: trust_col = next((c for c in raw_df.columns if '投信' in c), None)
        
    foreign_col = next((c for c in raw_df.columns if '外資' in c and ('買賣超' in c or '淨買' in c)), None)
    if not foreign_col: foreign_col = next((c for c in raw_df.columns if '外資' in c), None)
    
    if not code_col:
        return pd.DataFrame()
        
    # 絕對鐵門：只保留 4 碼純血普通股
    df_clean = raw_df[raw_df[code_col].str.match(r'^\d{4}$', na=False)].copy()
    df_clean['代號'] = df_clean[code_col]
    df_clean['名稱'] = df_clean[name_col] if name_col else '未知'
    
    def to_num(series):
        return pd.to_numeric(series.astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
        
    df_clean['投信買賣超'] = to_num(df_clean[trust_col]) if trust_col else 0
    df_clean['外資買賣超'] = to_num(df_clean[foreign_col]) if foreign_col else 0
    
    # 股數轉張數防呆機制
    if df_clean['投信買賣超'].abs().max() > 100000:
        df_clean['投信買賣超'] = df_clean['投信買賣超'] / 1000
        df_clean['外資買賣超'] = df_clean['外資買賣超'] / 1000
        
    return df_clean[['代號', '名稱', '投信買賣超', '外資買賣超']]
