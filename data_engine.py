import pandas as pd
import io

def clean_csv_data(uploaded_files):
    """負責讀取 CSV、破解 Big5 編碼、自動跳過廢話標題、清洗亂碼"""
    dfs = []
    for f in uploaded_files:
        try:
            raw_bytes = f.read()
            
            # 破解台灣官方專屬的 Big5 / cp950 編碼陷阱
            try:
                content = raw_bytes.decode('cp950', errors='ignore')
            except:
                content = raw_bytes.decode('utf-8', errors='ignore')
                
            lines = content.splitlines()
            
            # 智慧尋標：自動往下找，直到發現包含 '代號' 的那一行當作標題
            header_idx = 0
            for i, line in enumerate(lines):
                # 消除可能的空白與雙引號干擾
                clean_line = line.replace('"', '').replace(' ', '')
                if '代號' in clean_line or '代碼' in clean_line or '證券代號' in clean_line:
                    header_idx = i
                    break
            
            # 只讀取標題列之後的資料，徹底避開前面的廢話
            valid_csv_content = '\n'.join(lines[header_idx:])
            df = pd.read_csv(io.StringIO(valid_csv_content), dtype=str)
            
            # 清洗欄位名稱 (去除空白與雙引號)
            df.columns = df.columns.str.strip().str.replace('"', '')
            dfs.append(df)
        except Exception as e:
            continue
            
    if not dfs:
        return pd.DataFrame()
        
    raw_df = pd.concat(dfs, ignore_index=True)
    
    # 找出真正的欄位名稱
    code_col = next((c for c in raw_df.columns if '代號' in c or '代碼' in c), None)
    name_col = next((c for c in raw_df.columns if '名稱' in c), None)
    
    # 終極盲抓投信與外資
    trust_col = next((c for c in raw_df.columns if '投信' in c and ('買賣超' in c or '淨買' in c)), None)
    if not trust_col: trust_col = next((c for c in raw_df.columns if '投信' in c), None)
        
    foreign_col = next((c for c in raw_df.columns if '外資' in c and ('買賣超' in c or '淨買' in c)), None)
    if not foreign_col: foreign_col = next((c for c in raw_df.columns if '外資' in c), None)
    
    if not code_col:
        return pd.DataFrame()
        
    # 絕對鐵門：清理代號欄位的雙引號，並只保留 4 碼純血普通股
    raw_df[code_col] = raw_df[code_col].astype(str).str.replace('"', '').str.strip()
    df_clean = raw_df[raw_df[code_col].str.match(r'^\d{4}$', na=False)].copy()
    
    df_clean['代號'] = df_clean[code_col]
    df_clean['名稱'] = df_clean[name_col] if name_col else '未知'
    
    def to_num(series):
        return pd.to_numeric(series.astype(str).str.replace(',', '').str.replace('"', '').str.strip(), errors='coerce').fillna(0)
        
    df_clean['投信買賣超'] = to_num(df_clean[trust_col]) if trust_col else 0
    df_clean['外資買賣超'] = to_num(df_clean[foreign_col]) if foreign_col else 0
    
    # 股數轉張數防呆機制
    if df_clean['投信買賣超'].abs().max() > 100000:
        df_clean['投信買賣超'] = df_clean['投信買賣超'] / 1000
        df_clean['外資買賣超'] = df_clean['外資買賣超'] / 1000
        
    return df_clean[['代號', '名稱', '投信買賣超', '外資買賣超']]
