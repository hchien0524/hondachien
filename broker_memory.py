import sqlite3
import io
import zipfile
import os

class BrokerMemory:
    def __init__(self, db_name="hios_memory.db"):
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        """初始化 SQLite 資料庫"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        # 建立一個簡單的系統狀態表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def save_all(self):
        """強制將當前狀態存入資料庫"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO system_logs (action) VALUES ('Manual Backup Triggered')")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"存檔失敗: {e}")

    def backup_to_zip(self):
        """將 SQLite 資料庫打包成 ZIP 傳回給 Streamlit 下載"""
        try:
            if not os.path.exists(self.db_name):
                return None
                
            # 讀取資料庫檔案
            with open(self.db_name, 'rb') as f:
                db_data = f.read()

            # 建立 ZIP 緩衝區
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                # 將資料庫寫入 ZIP 檔內
                zf.writestr(self.db_name, db_data)
                
            zip_buffer.seek(0)
            return zip_buffer.getvalue()
        except Exception as e:
            print(f"ZIP 打包失敗: {e}")
            return None
