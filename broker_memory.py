import streamlit as st
import pandas as pd
import sqlite3
import os

DB_FILE = "broker_memory.db"

def render_memory_dashboard():
    st.header("🗄️ 歷史記憶庫 (主力籌碼檔案室)")
    st.markdown("這裡存放了所有經過 X 光狙擊並歸檔的主力分點數據。")
    
    if not os.path.exists(DB_FILE):
        st.warning("⚠️ 尚未建立資料庫，請先在【🎯 主力 X 光狙擊】中寫入資料。")
        return
        
    try:
        conn = sqlite3.connect(DB_FILE)
        
        # 檢查資料表是否存在
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='broker_records'")
        if not cursor.fetchone():
            st.warning("⚠️ 資料庫中尚無 `broker_records` 資料表，請先寫入資料。")
            conn.close()
            return
            
        # 讀取所有資料
        df = pd.read_sql_query("SELECT * FROM broker_records ORDER BY record_date DESC, net_vol DESC", conn)
        conn.close()
        
        if df.empty:
            st.info("📭 目前記憶庫中沒有任何主力數據。")
            return
            
        # 重新命名欄位以利顯示
        df.columns = ['日期', '股票代號', '分點名稱', '買進(張)', '賣出(張)', '買賣超(張)']
        
        # ==========================================
        # 🔍 戰情篩選器
        # ==========================================
        col1, col2 = st.columns(2)
        with col1:
            date_list = ["全部"] + df['日期'].unique().tolist()
            selected_date = st.selectbox("📅 選擇日期", date_list)
        with col2:
            stock_list = ["全部"] + df['股票代號'].unique().tolist()
            selected_stock = st.selectbox("🎯 選擇股票代號", stock_list)
            
        # 過濾資料
        filtered_df = df.copy()
        if selected_date != "全部":
            filtered_df = filtered_df[filtered_df['日期'] == selected_date]
        if selected_stock != "全部":
            filtered_df = filtered_df[filtered_df['股票代號'] == selected_stock]
            
        st.success(f"✅ 共找到 {len(filtered_df)} 筆主力紀錄")
        
        # ==========================================
        # 🦅 歷史戰情總結 (當選定特定股票時顯示)
        # ==========================================
        if selected_stock != "全部" and not filtered_df.empty:
            st.subheader(f"🦅 【{selected_stock}】 歷史戰情總結")
            
            # 計算該檔股票的歷史最大買賣超
            top_buy = filtered_df[filtered_df['買賣超(張)'] > 0].groupby('分點名稱')['買賣超(張)'].sum().sort_values(ascending=False)
            top_sell = filtered_df[filtered_df['買賣超(張)'] < 0].groupby('分點名稱')['買賣超(張)'].sum().sort_values(ascending=True)
            
            col_a, col_b = st.columns(2)
            with col_a:
                if not top_buy.empty:
                    st.metric("🔥 歷史最大鎖碼主力", top_buy.index[0], f"+{top_buy.iloc[0]} 張")
            with col_b:
                if not top_sell.empty:
                    st.metric("⚠️ 歷史最大倒貨主力", top_sell.index[0], f"{top_sell.iloc[0]} 張")
            st.divider()

        # 顯示完整表格
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
                    
    except Exception as e:
        st.error(f"讀取資料庫發生錯誤: {e}")
