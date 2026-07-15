import sqlite3
import io
import zipfile
import os
import pandas as pd
import streamlit as st

class BrokerMemory:
    def __init__(self, db_name="broker_memory.db"):
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        """初始化 SQLite 資料庫"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        # 建立系統日誌表 (備份用)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # 建立主力籌碼記憶表 (與狙擊室共用)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS broker_records (
                record_date TEXT,
                stock_id TEXT,
                broker_name TEXT,
                buy_vol INTEGER,
                sell_vol INTEGER,
                net_vol INTEGER,
                PRIMARY KEY (record_date, stock_id, broker_name)
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
            with open(self.db_name, 'rb') as f:
                db_data = f.read()
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(self.db_name, db_data)
            zip_buffer.seek(0)
            return zip_buffer.getvalue()
        except Exception as e:
            print(f"ZIP 打包失敗: {e}")
            return None

    def render_ui(self):
        """階段四：歷史記憶庫的 UI 介面"""
        st.markdown("### 🗄️ 主力籌碼歷史記憶庫")
        st.info("這裡存放了您在「X光狙擊室」中儲存的所有主力分點陣型，供您隨時調閱與覆盤。")
        
        try:
            conn = sqlite3.connect(self.db_name)
            # 讀取資料庫並轉為 Pandas DataFrame
            df = pd.read_sql_query("SELECT * FROM broker_records ORDER BY record_date DESC, net_vol DESC", conn)
            conn.close()
            
            if df.empty:
                st.warning("⚠️ 目前記憶庫中尚無資料。請先至「階段三：X光狙擊」抓取並寫入資料。")
                return
                
            # 重新命名欄位以利閱讀
            df.columns = ['記錄日期', '股票代號', '分點名稱', '買進(張)', '賣出(張)', '買賣超(張)']
            
            # 建立動態過濾器
            col1, col2 = st.columns(2)
            with col1:
                stock_filter = st.multiselect("🔍 篩選股票代號", options=df['股票代號'].unique())
            with col2:
                date_filter = st.multiselect("📅 篩選記錄日期", options=df['記錄日期'].unique())
                
            if stock_filter:
                df = df[df['股票代號'].isin(stock_filter)]
            if date_filter:
                df = df[df['記錄日期'].isin(date_filter)]
                
            # 顯示資料表
            st.dataframe(df, use_container_width=True)
            st.markdown(f"**📊 目前顯示共 {len(df)} 筆分點紀錄**")
            
        except Exception as e:
            st.error(f"讀取記憶庫失敗：{e}")
            st.info("💡 若尚未建立資料表，請先至「階段三」儲存一筆資料。")
