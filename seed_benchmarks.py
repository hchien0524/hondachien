import sqlite3
from datetime import datetime

def setup_and_seed_benchmarks():
    """
    建立戰略基準資料表，並寫入 2026/07/07 的菁英名單
    """
    print("🚀 啟動 V32 戰略基準資料庫建檔程序...")
    
    # 1. 連線到 SQLite 資料庫 (如果檔案不存在會自動建立)
    conn = sqlite3.connect('broker_memory.db')
    cursor = conn.cursor()
    
    # 2. 建立資料表 (包含複合主鍵，確保同一天同一檔股票不重複)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS strategic_benchmarks (
            record_date TEXT,
            stock_id TEXT,
            stock_name TEXT,
            rating TEXT,
            strategy_type TEXT,
            key_brokers TEXT,
            entry_bias REAL,
            PRIMARY KEY (record_date, stock_id)
        )
    ''')
    
    # 3. 準備寫入語法 (UPSERT 邏輯：遇到重複的主鍵就更新資料)
    insert_sql = '''
        INSERT INTO strategic_benchmarks 
        (record_date, stock_id, stock_name, rating, strategy_type, key_brokers, entry_bias)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(record_date, stock_id) 
        DO UPDATE SET 
            rating=excluded.rating,
            strategy_type=excluded.strategy_type,
            key_brokers=excluded.key_brokers,
            entry_bias=excluded.entry_bias
    '''
    
    # 4. 寫入今日 (2026-07-07) 的菁英名單
    today_str = "2026-07-07"
    
    elite_list = [
        # --- 大戶避險金庫 (S/A 級) ---
        ("1722", "台肥", "S", "大戶避險金庫", "摩根大通, 美商高盛", 0.0),
        ("2820", "華票", "S", "大戶避險金庫", "摩根大通, 摩根士丹利", 0.0),
        ("2617", "台航", "S", "大戶避險金庫", "摩根大通, 凱基台北", 0.0),
        ("1201", "味全", "A-", "大戶避險金庫", "南部大戶連線, 凱基台北", 0.0),
        
        # --- 投信鐵三角 (金融/攻擊手) ---
        ("2855", "統一證", "A+", "投信鐵三角-金融", "投信", 1.87),
        ("2845", "遠東銀", "A+", "投信鐵三角-金融", "投信", 1.44),
        ("5876", "上海商銀", "A", "投信鐵三角-金融", "投信", 0.35),
        
        # --- 投信鐵三角 (AI 肉盾) ---
        ("2356", "英業達", "A", "投信鐵三角-AI肉盾", "投信", -1.86),
        ("2377", "微星", "A", "投信鐵三角-AI肉盾", "投信", -0.67),
        ("2382", "廣達", "A", "投信鐵三角-AI肉盾", "投信", 0.31),
        ("3231", "緯創", "A", "投信鐵三角-AI肉盾", "投信", -1.91),
        ("2376", "技嘉", "A", "投信鐵三角-AI肉盾", "投信", -3.60),
        
        # --- 投信鐵三角 (運輸避風港) ---
        ("2610", "華航", "A", "投信鐵三角-運輸", "投信", 0.16),
        ("2618", "長榮航", "A", "投信鐵三角-運輸", "投信", 1.10),
        ("2633", "台灣高鐵", "A", "投信鐵三角-運輸", "投信", 1.22),
        ("2646", "星宇航空", "A", "投信鐵三角-運輸", "投信", 1.13)
    ]
    
    # 5. 執行批次寫入
    records = [(today_str, *item) for item in elite_list]
    cursor.executemany(insert_sql, records)
    conn.commit()
    
    # 6. 驗證寫入結果並印出
    cursor.execute("SELECT COUNT(*) FROM strategic_benchmarks WHERE record_date = ?", (today_str,))
    count = cursor.fetchone()[0]
    print(f"✅ 報告總司令：成功將 {count} 檔菁英標的寫入戰略資料庫！")
    
    # 隨機印出幾筆讓您確認
    print("-" * 30)
    cursor.execute("SELECT stock_id, stock_name, strategy_type FROM strategic_benchmarks LIMIT 5")
    for row in cursor.fetchall():
        print(f"入庫確認 -> 代號: {row[0]}, 名稱: {row[1]}, 戰略定位: {row[2]}")
    print("-" * 30)
    
    conn.close()

# 執行建檔
if __name__ == "__main__":
    setup_and_seed_benchmarks()
