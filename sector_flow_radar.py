import streamlit as st
import pandas as pd
import sqlite3
import requests
import datetime
import re

class SectorFlowRadar:
    def __init__(self, db_name="broker_memory.db"):
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        """初始化族群資金歷史資料表"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sector_flow_history (
                    record_date TEXT,
                    sector_name TEXT,
                    trade_value REAL,
                    percentage REAL,
                    PRIMARY KEY (record_date, sector_name)
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"資料庫初始化失敗: {e}")

    def fetch_twse_sector_data(self):
        url = "https://openapi.twse.com.tw/v1/exchangeReport/BFIAMU"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64 )'}
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code != 200:
                return None, f"連線失敗 (HTTP {response.status_code})"
                
            try:
                data = response.json()
            except Exception:
                return None, "證交所防火牆阻擋了雲端 IP，請使用下方的「手動備用彈匣」。"
                
            if not data or len(data) == 0:
                return None, "今日 OpenAPI 尚無數據。"
                
            parsed_data = []
            total_market_value = 0.0
            
            for row in data:
                sector_name = row.get('IndexClasses', '').strip()
                if sector_name in ['總計', '合計', '電子工業', '未含金融電子股', '未含金融股', '電子類指數', '金融保險類指數', '未含電子股']:
                    continue
                try: trade_value = float(row.get('TradeValue', 0))
                except: trade_value = 0.0
                    
                parsed_data.append({'sector_name': sector_name, 'trade_value': trade_value})
                total_market_value += trade_value
                
            for item in parsed_data:
                item['percentage'] = round((item['trade_value'] / total_market_value) * 100, 2) if total_market_value > 0 else 0.0
                    
            df = pd.DataFrame(parsed_data)
            record_date = datetime.datetime.now().strftime("%Y-%m-%d")
            return df, record_date
            
        except Exception as e:
            return None, f"連線異常: {e} (請使用手動備用彈匣)"

    def parse_manual_data(self, raw_text):
        """解析總司令手動貼上的證交所表格數據"""
        parsed_data = []
        lines = raw_text.strip().split('\n')
        
        for line in lines:
            parts = re.split(r'\s+', line.strip())
            if len(parts) >= 3:
                sector_name = parts[0]
                if sector_name in ['總計', '合計', '電子工業', '未含金融電子股', '未含金融股', '電子類指數', '金融保險類指數', '未含電子股']:
                    continue
                try:
                    trade_value = float(parts[1].replace(',', ''))
                    percentage = float(parts[2].replace('%', '').replace(',', ''))
                    parsed_data.append({
                        'sector_name': sector_name,
                        'trade_value': trade_value,
                        'percentage': percentage
                    })
                except ValueError:
                    continue
                    
        if parsed_data:
            return pd.DataFrame(parsed_data)
        return None

    def save_to_db(self, df, record_date):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            insert_sql = '''
                INSERT INTO sector_flow_history (record_date, sector_name, trade_value, percentage)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(record_date, sector_name) 
                DO UPDATE SET trade_value=excluded.trade_value, percentage=excluded.percentage
            '''
            records = [(record_date, row['sector_name'], row['trade_value'], row['percentage']) for _, row in df.iterrows()]
            cursor.executemany(insert_sql, records)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            st.error(f"寫入資料庫失敗: {e}")
            return False

    def analyze_invisible_champions(self):
        try:
            conn = sqlite3.connect(self.db_name)
            dates_query = "SELECT DISTINCT record_date FROM sector_flow_history ORDER BY record_date DESC LIMIT 3"
            dates_df = pd.read_sql_query(dates_query, conn)
            
            if len(dates_df) < 3:
                conn.close()
                return None, f"⚠️ 歷史數據不足！目前僅有 {len(dates_df)} 天數據，需累積 3 天才能啟動隱形冠軍濾網。"
                
            recent_dates = dates_df['record_date'].tolist()
            recent_dates.sort() 
            d1, d2, d3 = recent_dates[0], recent_dates[1], recent_dates[2]
            
            data_query = f"SELECT * FROM sector_flow_history WHERE record_date IN ('{d1}', '{d2}', '{d3}')"
            df_all = pd.read_sql_query(data_query, conn)
            conn.close()
            
            df_pivot = df_all.pivot(index='sector_name', columns='record_date', values='percentage').reset_index().dropna()
            
            champions = df_pivot[(df_pivot[d1] < df_pivot[d2]) & (df_pivot[d2] < df_pivot[d3])].copy()
            if not champions.empty:
                champions['3日增幅(%)'] = round(champions[d3] - champions[d1], 2)
                champions = champions.sort_values(by='3日增幅(%)', ascending=False).reset_index(drop=True)
                
            return champions, recent_dates
        except Exception as e:
            return None, f"分析失敗: {e}"

    def render_ui(self):
        st.header("🌊 階段一：族群資金活水 (Top-Down 宏觀雷達)")
        st.markdown("追蹤各類股資金流向，精準抓出**「連續 3 天資金偷偷流入」**的隱形冠軍板塊！")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("🔄 1. 自動獲取今日資金 (雲端易受阻)", type="primary", use_container_width=True):
                with st.spinner("連線中..."):
                    df_today, result = self.fetch_twse_sector_data()
                    if df_today is not None:
                        if self.save_to_db(df_today, result): st.success(f"✅ 成功歸檔 {result} 數據！")
                    else:
                        st.error(result)
                        
        with col2:
            st.markdown("🔗 **🕵️‍♂️ 官方查帳直達車：** [點我前往 TWSE 證交所官方網頁](https://www.twse.com.tw/zh/trading/historical/bfiamu.html )")
            st.caption("💡 若自動獲取失敗，請點擊上方連結，將表格內容複製並貼到下方。")

        with st.expander("📥 手動備用彈匣 (若自動連線失敗請用此處)", expanded=True):
            manual_date = st.date_input("選擇數據日期", datetime.date.today())
            manual_data = st.text_area("請貼上證交所表格數據 (包含族群、金額、佔比)：", height=150, placeholder="半導體類指數 398665864184 37.18\n電子零組件類指數 290558443046 27.09...")
            
            if st.button("💾 解析並寫入記憶庫"):
                if manual_data.strip():
                    df_manual = self.parse_manual_data(manual_data)
                    if df_manual is not None and not df_manual.empty:
                        date_str = manual_date.strftime("%Y-%m-%d")
                        if self.save_to_db(df_manual, date_str):
                            st.success(f"✅ 成功解析並歸檔 {date_str} 的資金數據！")
                    else:
                        st.error("❌ 解析失敗，請確認貼上的格式是否正確。")
                else:
                    st.warning("⚠️ 請先貼上數據！")

        st.divider()
        
        st.subheader("👑 隱形冠軍戰報 (連續 3 天資金流入)")
        champions, dates_info = self.analyze_invisible_champions()
        
        if isinstance(dates_info, str): 
            st.warning(dates_info)
        elif champions is not None and not champions.empty:
            d1, d2, d3 = dates_info[0], dates_info[1], dates_info[2]
            st.success(f"🎯 發現資金正在偷偷建倉！比對區間：{d1} ➔ {d3}")
            
            display_df = champions[['sector_name', d1, d2, d3, '3日增幅(%)']].copy()
            display_df.columns = ['族群名稱', f'{d1} 佔比(%)', f'{d2} 佔比(%)', f'最新 {d3} 佔比(%)', '3日總增幅(%)']
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("📉 目前無任何族群符合「連續 3 天資金流入」的嚴格標準。")

        with st.expander("📊 展開查看最新族群原始資金佔比 (供查帳驗算)"):
            try:
                conn = sqlite3.connect(self.db_name)
                latest_date = pd.read_sql_query("SELECT MAX(record_date) FROM sector_flow_history", conn).iloc[0,0]
                if latest_date:
                    df_raw = pd.read_sql_query(f"SELECT sector_name AS '族群名稱', trade_value AS '成交金額(元)', percentage AS '資金佔比(%)' FROM sector_flow_history WHERE record_date = '{latest_date}' ORDER BY percentage DESC", conn)
                    st.write(f"📅 數據日期：{latest_date}")
                    st.dataframe(df_raw, use_container_width=True)
                else:
                    st.write("尚無歷史數據。")
                conn.close()
            except Exception:
                st.write("無法讀取原始數據。")
