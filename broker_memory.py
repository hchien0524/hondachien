import sqlite3
import pandas as pd
import os

# 🛡️ 設定資料庫檔案名稱
DB_PATH = 'broker_memory.db'

def init_db():
    """初始化資料庫與資料表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 建立籌碼資料表 (加入 UNIQUE 約束，防止同一天重複寫入)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS broker_data (
            date TEXT,
            stock_id TEXT,
            broker_name TEXT,
            buy_vol INTEGER,
            sell_vol INTEGER,
            net_vol INTEGER,
            UNIQUE(date, stock_id, broker_name)
        )
    ''')
    conn.commit()
    conn.close()

def save_daily_data(date_str, stock_id, df):
    """將單日籌碼存入資料庫"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 🌟 強制轉為字串並去除空白，防止型別脫鉤
        stock_id = str(stock_id).strip()
        
        for index, row in df.iterrows():
            broker_name = str(row['券商名稱']).strip()
            buy_vol = int(row['買進張數'])
            sell_vol = int(row['賣出張數'])
            net_vol = int(row['買賣超張數'])
            
            # 🌟 使用 INSERT OR REPLACE，如果今天已經狙擊過，就覆蓋更新，不會報錯
            cursor.execute('''
                INSERT OR REPLACE INTO broker_data 
                (date, stock_id, broker_name, buy_vol, sell_vol, net_vol)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (date_str, stock_id, broker_name, buy_vol, sell_vol, net_vol))
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ 資料庫寫入失敗: {e}")
        return False

def get_multi_day_concentration(stock_id, days=5):
    """調閱過去 N 天的歷史籌碼加總"""
    try:
        conn = sqlite3.connect(DB_PATH)
        # 🌟 強制轉為字串，確保查詢條件一致
        stock_id = str(stock_id).strip()
        
        # 1. 先找出這檔股票最近的 N 個交易日
        query_dates = f"""
            SELECT DISTINCT date FROM broker_data 
            WHERE stock_id = '{stock_id}' 
            ORDER BY date DESC LIMIT {days}
        """
        dates_df = pd.read_sql_query(query_dates, conn)
        
        if dates_df.empty:
            conn.close()
            return None
            
        min_date = dates_df['date'].min()
        max_date = dates_df['date'].max()
        
        # 2. 針對這些日期，進行券商買賣超加總
        query_data = f"""
            SELECT broker_name as 券商名稱, 
                   SUM(buy_vol) as 區間買進, 
                   SUM(sell_vol) as 區間賣出, 
                   SUM(net_vol) as 區間買賣超
            FROM broker_data
            WHERE stock_id = '{stock_id}' AND date >= '{min_date}' AND date <= '{max_date}'
            GROUP BY broker_name
            ORDER BY 區間買賣超 DESC
        """
        result_df = pd.read_sql_query(query_data, conn)
        conn.close()
        
        if result_df.empty:
            return None
            
        # 3. 只回傳前 15 大買超與前 15 大賣超主力 (讓畫面更乾淨)
        top_buy = result_df.head(15)
        top_sell = result_df.tail(15).sort_values(by='區間買賣超', ascending=True)
        
        # 合併並回傳
        final_df = pd.concat([top_buy, top_sell]).drop_duplicates().reset_index(drop=True)
        return final_df
        
    except Exception as e:
        print(f"❌ 資料庫查詢失敗: {e}")
        return None
