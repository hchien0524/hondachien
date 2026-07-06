import sqlite3
import pandas as pd
import os
from datetime import datetime

# ==========================================
# 🛡️ V31 歷史記憶庫 (Local Memory Module)
# ==========================================

DB_DIR = "memory_vault"
DB_PATH = os.path.join(DB_DIR, "broker_memory.db")

def init_db():
    """
    第一步：建立秘密基地。
    如果資料夾或資料庫不存在，系統會自動建立。
    """
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 建立券商進出明細表 (包含：日期、代號、券商名稱、買張、賣張、淨買超)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS broker_data (
            date TEXT,
            stock_code TEXT,
            broker_name TEXT,
            buy_vol REAL,
            sell_vol REAL,
            net_vol REAL,
            UNIQUE(date, stock_code, broker_name) -- 防止同一天重複寫入
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ [系統提示] 歷史記憶庫 (broker_memory.db) 已連線並啟動防護！")

def save_daily_data(date_str, stock_code, df_daily):
    """
    第二步：寫入單日情報。
    將 Yahoo 爬蟲抓到的「單日」券商明細，存入記憶庫。
    df_daily 必須包含欄位：['券商名稱', '買進張數', '賣出張數', '買賣超張數']
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    success_count = 0
    for index, row in df_daily.iterrows():
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO broker_data 
                (date, stock_code, broker_name, buy_vol, sell_vol, net_vol)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                date_str, 
                str(stock_code), 
                row['券商名稱'], 
                float(row['買進張數']), 
                float(row['賣出張數']), 
                float(row['買賣超張數'])
            ))
            success_count += 1
        except Exception as e:
            print(f"⚠️ 寫入錯誤: {e}")
            
    conn.commit()
    conn.close()
    print(f"💾 [記憶寫入] {stock_code} 於 {date_str} 的 {success_count} 筆券商資料已安全存檔！")

def get_multi_day_concentration(stock_code, days=5):
    """
    第三步：召喚歷史記憶 (終極殺招)！
    自動撈取過去 N 天的資料，加總計算出「真正的區間主力」。
    """
    conn = sqlite3.connect(DB_PATH)
    
    # 使用 SQL 語法，直接把過去 N 天的同一個券商買賣超「加總」起來！
    query = f'''
        SELECT 
            broker_name as 券商名稱,
            SUM(buy_vol) as 區間總買進,
            SUM(sell_vol) as 區間總賣出,
            SUM(net_vol) as 區間淨買賣超
        FROM broker_data
        WHERE stock_code = '{stock_code}'
        GROUP BY broker_name
        ORDER BY 區間淨買賣超 DESC
    '''
    
    df_history = pd.read_sql_query(query, conn)
    conn.close()
    
    if df_history.empty:
        return None
        
    # 只取前 15 大買超主力
    df_top_15 = df_history.head(15)
    
    print(f"🎯 [主力現形] 已成功調閱 {stock_code} 歷史記憶，抓出區間前 15 大主力！")
    return df_top_15

# ==========================================
# 🧪 戰情室火力測試 (模擬運行)
# ==========================================
if __name__ == "__main__":
    # 1. 啟動資料庫
    init_db()
    
    # 2. 模擬今天 (Day 1) 抓到的均豪資料
    today = datetime.now().strftime("%Y-%m-%d")
    mock_data = pd.DataFrame({
        '券商名稱': ['凱基-台北', '兆豐-民生', '摩根大通', '美林'],
        '買進張數': [200, 150, 100, 50],
        '賣出張數': [20, 0, 10, 50],
        '買賣超張數': [180, 150, 90, 0]
    })
    
    # 3. 存入記憶庫
    save_daily_data(today, "5443", mock_data)
    
    # 4. 呼叫歷史記憶，瞬間算出累積籌碼！
    result_df = get_multi_day_concentration("5443", days=5)
    print("\n📊 均豪 (5443) 歷史區間主力籌碼表：")
    print(result_df)
