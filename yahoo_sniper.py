import streamlit as st
import pandas as pd
import re
import sqlite3
from datetime import datetime
import requests
from bs4 import BeautifulSoup

def render_sniper_module():
    st.header("🎯 主力 X 光狙擊室 (全自動聯網版)")
    st.markdown("一鍵自動潛入 Yahoo 股市，抓取主力分點數據並寫入記憶庫。")
    
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
    # 🧠 核心解析引擎 (共用邏輯)
    # ==========================================
    def parse_broker_data(lines):
        parsed_data = []
        is_yahoo = any("買超券商" in line or "賣超券商" in line for line in lines)
        
        if is_yahoo:
            headers = {"買超券商", "買進", "賣出", "買超張數", "賣超券商", "賣超張數"}
            filtered = [l for l in lines if l not in headers]
            
            i = 0
            while i < len(filtered) - 3:
                broker = filtered[i]
                try:
                    buy = int(filtered[i+1].replace(',', ''))
                    sell = int(filtered[i+2].replace(',', ''))
                    net = int(filtered[i+3].replace(',', ''))
                    parsed_data.append({
                        "分點名稱": broker,
                        "買進(張)": buy,
                        "賣出(張)": sell,
                        "買賣超(張)": net
                    })
                    i += 4
                except ValueError:
                    i += 1
        else:
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
        return parsed_data

    # ==========================================
    # 🌐 引擎 A：全自動聯網抓取 (Yahoo 爬蟲)
    # ==========================================
    st.subheader("🚀 第一步：獲取主力籌碼")
    if st.button("🌐 全自動聯網抓取 (Yahoo 主力進出)", type="primary", use_container_width=True):
        if not stock_id:
            st.warning("⚠️ 請先輸入股票代號！")
            return
            
        with st.spinner(f"正在潛入 Yahoo 戰情網抓取 {stock_id} 主力數據..."):
            try:
                url = f"https://tw.stock.yahoo.com/quote/{stock_id}/broker-trading"
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64 )'}
                res = requests.get(url, headers=headers, timeout=10)
                
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, 'html.parser')
                    # 萃取網頁中所有文字並逐行清理
                    lines = [text.strip() for text in soup.stripped_strings]
                    
                    parsed_data = parse_broker_data(lines)
                    
                    if parsed_data:
                        st.session_state['sniper_data'] = parsed_data
                        st.success(f"✅ 成功從 Yahoo 自動抓取 【{stock_id}】 的主力陣型！")
                    else:
                        st.error("❌ 抓取失敗：今日可能無數據，或 Yahoo 網頁結構變更。")
                else:
                    st.error(f"❌ 無法連線至 Yahoo 股市 (HTTP {res.status_code})")
            except Exception as e:
                st.error(f"🌐 網路連線異常: {e}")

    # ==========================================
    # 📥 引擎 B：手動備用彈匣 (防禦機制)
    # ==========================================
    with st.expander("📥 手動備用彈匣 (若自動抓取失敗，可展開此處手動貼上)"):
        raw_data = st.text_area("請貼上主力分點買賣超數據：", height=150)
        if st.button("🔫 手動解析數據"):
            if raw_data.strip():
                lines = [line.strip() for line in raw_data.strip().split('\n') if line.strip()]
                parsed_data = parse_broker_data(lines)
                if parsed_data:
                    st.session_state['sniper_data'] = parsed_data
                    st.success("✅ 手動解析成功！")
                else:
                    st.error("❌ 解析失敗，請確認格式。")

    # ==========================================
    # 📊 顯示結果與寫入記憶庫
    # ==========================================
    if 'sniper_data' in st.session_state and st.session_state['sniper_data']:
        df = pd.DataFrame(st.session_state['sniper_data'])
        df = df.sort_values(by="買賣超(張)", ascending=False).reset_index(drop=True)
        
        st.divider()
        st.subheader("🦅 CIO 戰情速報")
        top_buy = df[df['買賣超(張)'] > 0]
        top_sell = df[df['買賣超(張)'] < 0].sort_values(by="買賣超(張)", ascending=True)
        
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
        # 💾 第二步：一鍵寫入歷史記憶庫
        # ==========================================
        st.subheader("💾 第二步：資料歸檔")
        if st.button("💾 將此陣型寫入歷史記憶庫 (broker_memory)", type="primary", use_container_width=True):
            try:
                conn = sqlite3.connect('broker_memory.db')
                cursor = conn.cursor()
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
                records = [(today_str, stock_id, row['分點名稱'], row['買進(張)'], row['賣出(張)'], row['買賣超(張)']) for _, row in df.iterrows()]
                
                cursor.executemany('''
                    INSERT INTO broker_records (record_date, stock_id, broker_name, buy_vol, sell_vol, net_vol)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(record_date, stock_id, broker_name) 
                    DO UPDATE SET buy_vol=excluded.buy_vol, sell_vol=excluded.sell_vol, net_vol=excluded.net_vol
                ''', records)
                
                conn.commit()
                conn.close()
                st.success(f"✅ 已成功將 {stock_id} 的主力陣型寫入資料庫！您可至【🗄️ 歷史記憶庫】調閱。")
            except Exception as e:
                st.error(f"寫入資料庫失敗: {e}")
