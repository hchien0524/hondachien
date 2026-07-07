import sqlite3
import pandas as pd
import os
from datetime import datetime
import streamlit as st

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

# 🌟 CIO 修復：新增對接 yahoo_sniper 的專用接口
def save_daily_chips(stock_id, df):
    """提供給 yahoo_sniper.py 呼叫的介面，自動抓取今日日期"""
    init_db() # 確保資料庫存在
    today_str = datetime.now().strftime("%Y-%m-%d")
    return save_daily_data(today_str, stock_id, df)

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

# ==========================================
# 🖥️ Streamlit UI 介面渲染模組 (對接 app.py Tab 6)
# ==========================================
def render_memory_dashboard():
    st.header("🗄️ 歷史記憶庫 (主力籌碼 X 光)")
    st.caption("調閱過去狙擊成功的歷史籌碼，自動加總多日數據，抓出真正的波段黑手！")
    
    init_db() # 確保資料庫已初始化
    
    # 取得持股/觀察名單作為下拉選單選項
    watchlist = st.session_state.get('watchlist', [])
    portfolio = st.session_state.get('portfolio', [])
    
    # 整理所有代號
    all_items = watchlist + portfolio
    options = []
    seen = set()
    for item in all_items:
        code = str(item.get('代號', item.get('code', '')))
        name = str(item.get('名稱', item.get('name', '')))
        if code and code not in seen:
            options.append(f"{code} - {name}")
            seen.add(code)
            
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if options:
            selected_option = st.selectbox("請選擇要調閱的股票：", ["-- 請選擇 --"] + options)
            if selected_option != "-- 請選擇 --":
                target_code = selected_option.split(" - ")[0]
            else:
                target_code = ""
        else:
            target_code = st.text_input("請輸入股票代號 (例如: 2376)：")
            
    with col2:
        days = st.number_input("調閱天數 (預設 5 天)", min_value=1, max_value=60, value=5)
        
    if st.button("🔍 調閱歷史記憶", type="primary"):
        if not target_code:
            st.warning("⚠️ 請先選擇或輸入股票代號！")
            return
            
        with st.spinner(f"正在調閱 {target_code} 過去 {days} 天的籌碼記憶..."):
            df_result = get_multi_day_concentration(target_code, days)
            
            if df_result is not None and not df_result.empty:
                st.success(f"✅ 成功調閱 {target_code} 的歷史籌碼！")
                st.dataframe(df_result, use_container_width=True)
            else:
                st.error(f"❌ 記憶庫中沒有 {target_code} 的歷史資料，請先到 Tab 5 進行狙擊存檔！")
