import streamlit as st
import pandas as pd
import re
import sqlite3
from datetime import datetime

def render_sniper_module():
    st.header("🎯 主力 X 光狙擊室")
    st.markdown("支援解析 **Yahoo 股市格式** 與 **券商軟體格式**，並可一鍵寫入歷史記憶庫。")
    
    # ==========================================
    # 🎯 自動填彈系統
    # ==========================================
    if 'target_id' not in st.session_state:
        st.session_state['target_id'] = ""
        
    col1, col2 = st.columns([1, 2])
    with col1:
        stock_id = st.text_input("🎯 狙擊目標 (股票代號)", key="target_id")
    
    with col2:
        st.info("💡 提示：在【🔥 終極戰報】點擊「一鍵上膛」後，代號會自動填入此處。")

    # ==========================================
    # 📥 數據輸入區
    # ==========================================
    raw_data = st.text_area(
        "📥 請貼上主力分點買賣超數據 (支援 Yahoo 網頁複製 或 券商軟體複製)：", 
        height=200,
        placeholder="請直接貼上從 Yahoo 股市或券商軟體複製的數據..."
    )
    
    # ==========================================
    # 🔫 雙引擎解析邏輯
    # ==========================================
    if st.button("🔫 啟動 X 光掃描", type="primary", use_container_width=True):
        if not stock_id:
            st.warning("⚠️ 請先輸入股票代號！")
            return
        if not raw_data.strip():
            st.warning("⚠️ 請貼上籌碼數據！")
            return
            
        with st.spinner("正在解碼主力籌碼陣型..."):
            parsed_data = []
            # 清理空白行
            lines = [line.strip() for line in raw_data.strip().split('\n') if line.strip()]
            
            # 判斷是否為 Yahoo 格式 (特徵：包含特定表頭)
            is_yahoo_format = any("買超券商" in line or "賣超券商" in line for line in lines)
            
            if is_yahoo_format:
                # 🛡️ 引擎 A：Yahoo 垂直格式解析
                headers = {"買超券商", "買進", "賣出", "買超張數", "賣超券商", "賣超張數"}
                filtered_lines = [line for line in lines if line not in headers]
                
                # 每 4 行為一筆資料 (券商名稱, 買進, 賣出, 買賣超)
                for i in range(0, len(filtered_lines) - 3, 4):
                    broker = filtered_lines[i]
                    try:
                        buy = int(filtered_lines[i+1].replace(',', ''))
                        sell = int(filtered_lines[i+2].replace(',', ''))
                        net = int(filtered_lines[i+3].replace(',', ''))
                        parsed_data.append({
                            "分點名稱": broker,
                            "買進(張)": buy,
                            "賣出(張)": sell,
                            "買賣超(張)": net
                        })
                    except ValueError:
                        continue
            else:
                # 🛡️ 引擎 B：券商軟體水平格式解析
                for line in lines:
                    parts = re.split(r'\s+', line)
                    if len(parts) >= 4:
                        try:
                            net = int(parts[-1].replace(',', ''))
                            sell = int(parts[-2].replace(',', ''))
                            buy = int(parts[-3].replace(',', ''))
                            broker_name = " ".join(parts[:-3])
                            broker_name = re.sub(r'^\d+\s+', '', broker_name)
                            parsed_data.append({
                                "分點名稱": broker_name,
                                "買進(張)": buy,
                                "賣出(張)": sell,
                                "買賣超(張)": net
                            })
                        except ValueError:
                            continue
            
            if parsed_data:
                st.session_state['sniper_data'] = parsed_data
                st.success(f"✅ 成功解碼 【{stock_id}】 的主力陣型！")
            else:
                st.error("❌ 數據解析失敗，請確認貼上的數據格式。")

    # ==========================================
    # 📊 顯示結果與寫入記憶庫
    # ==========================================
    if 'sniper_data' in st.session_state and st.session_state['sniper_data']:
        df = pd.DataFrame(st.session_state['sniper_data'])
        df = df.sort_values(by="買賣超(張)", ascending=False).reset_index(drop=True)
        
        # 🦅 CIO 戰情速報
        top_buy = df[df['買賣超(張)'] > 0]
        top_sell = df[df['買賣超(張)'] < 0].sort_values(by="買賣超(張)", ascending=True)
        
        st.subheader("🦅 CIO 戰情速報")
        col_a, col_b = st.columns(2)
        with col_a:
            if not top_buy.empty:
                st.metric("🔥 最大鎖碼主力", top_buy.iloc[0]['分點名稱'], f"+{top_buy.iloc[0]['買賣超(張)']} 張")
            else:
                st.metric("🔥 最大鎖碼主力", "無", "0 張")
                
        with col_b:
            if not top_sell.empty:
                st.metric("⚠️ 最大倒貨主力", top_sell.iloc[0]['分點名稱'], f"{top_sell.iloc[0]['買賣超(張)']} 張")
            else:
                st.metric("⚠️ 最大倒貨主力", "無", "0 張")
                
        st.dataframe(df, use_container_width=True)
        
        # ==========================================
        # 💾 一鍵寫入歷史記憶庫 (broker_memory)
        # ==========================================
        st.divider()
        if st.button("💾 將此陣型寫入歷史記憶庫", type="primary"):
            try:
                conn = sqlite3.connect('broker_memory.db')
                cursor = conn.cursor()
                
                # 確保資料表存在
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
                
                today_str = datetime.now().strftime("%Y-%m-%d")
                records = []
                for _, row in df.iterrows():
                    records.append((
                        today_str,
                        stock_id,
                        row['分點名稱'],
                        row['買進(張)'],
                        row['賣出(張)'],
                        row['買賣超(張)']
                    ))
                
                # 寫入資料庫 (若重複則更新)
                cursor.executemany('''
                    INSERT INTO broker_records (record_date, stock_id, broker_name, buy_vol, sell_vol, net_vol)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(record_date, stock_id, broker_name) 
                    DO UPDATE SET buy_vol=excluded.buy_vol, sell_vol=excluded.sell_vol, net_vol=excluded.net_vol
                ''', records)
                
                conn.commit()
                conn.close()
                st.success(f"✅ 已成功將 {stock_id} 的主力陣型寫入 `broker_memory.db`！您可至【🗄️ 歷史記憶庫】調閱。")
            except Exception as e:
                st.error(f"寫入資料庫失敗: {e}")
