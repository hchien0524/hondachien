import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time

def render_sniper_module():
    st.header("🎯 主力 X 光狙擊室 (全自動聯網版)")
    st.markdown("已連接全球戰情網，可全自動抓取 Yahoo 股市主力進出明細。")
    
    # ==========================================
    # 🎯 自動填彈系統：強制綁定 Session State
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
        for line in lines:
            # 將多個空白壓縮成單一空白
            parts = re.split(r'\s+', line.strip())
            if len(parts) >= 4:
                try:
                    net = int(parts[-1].replace(',', ''))
                    sell = int(parts[-2].replace(',', ''))
                    buy = int(parts[-3].replace(',', ''))
                    broker_name = " ".join(parts[:-3])
                    broker_name = re.sub(r'^\d+\s+', '', broker_name)
                    
                    # 過濾掉表頭雜訊
                    if "券商" in broker_name or "買進" in broker_name or "賣出" in broker_name: 
                        continue
                        
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
    # 🌐 全自動聯網狙擊 (Yahoo 爬蟲)
    # ==========================================
    if st.button("🌐 自動聯網狙擊 (抓取 Yahoo 主力籌碼)", type="primary", use_container_width=True):
        if not stock_id:
            st.warning("⚠️ 請先輸入或上膛股票代號！")
            return
            
        with st.spinner(f"正在潛入 Yahoo 戰情網抓取 {stock_id} 主力數據..."):
            try:
                # 建立多重 URL 測試 (上市 .TW / 上櫃 .TWO)
                urls = [
                    f"https://tw.stock.yahoo.com/quote/{stock_id}.TW/broker-trading",
                    f"https://tw.stock.yahoo.com/quote/{stock_id}.TWO/broker-trading",
                    f"https://tw.stock.yahoo.com/quote/{stock_id}/broker-trading"
                ]
                
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64 ) AppleWebKit/537.36'}
                html_content = ""
                
                # 尋找有效的網頁回應
                for url in urls:
                    res = requests.get(url, headers=headers, timeout=5)
                    if res.status_code == 200:
                        html_content = res.text
                        break
                
                if html_content:
                    soup = BeautifulSoup(html_content, 'html.parser')
                    # Yahoo 的表格通常是用 li 標籤包裝，我們把 li 裡面的文字用空白隔開萃取出來
                    lines = [li.get_text(separator=' ') for li in soup.find_all('li')]
                    parsed_data = parse_broker_data(lines)
                    
                    if parsed_data:
                        st.session_state['sniper_data'] = parsed_data
                        st.success(f"✅ 成功從 Yahoo 自動抓取 【{stock_id}】 的主力陣型！")
                    else:
                        st.error("❌ 自動抓取失敗：Yahoo 網頁結構可能改變，或該檔股票今日無數據。")
                else:
                    st.error("❌ 無法連線至 Yahoo 股市，請稍後再試。")
            except Exception as e:
                st.error(f"🌐 網路連線異常: {e}")

    st.divider()
    
    # ==========================================
    # 📥 手動備用彈匣 (防禦 Yahoo 封鎖 IP)
    # ==========================================
    with st.expander("📥 手動備用彈匣 (若自動抓取失敗，請展開此處貼上數據)"):
        st.markdown(f"👉 [點我手動前往 Yahoo {stock_id} 籌碼頁面](https://tw.stock.yahoo.com/quote/{stock_id}/broker-trading )")
        raw_data = st.text_area("請貼上主力分點買賣超數據：", height=150)
        if st.button("🔫 手動解析數據"):
            if raw_data.strip():
                lines = raw_data.strip().split('\n')
                parsed_data = parse_broker_data(lines)
                if parsed_data:
                    st.session_state['sniper_data'] = parsed_data
                    st.success("✅ 手動解析成功！")
                else:
                    st.error("❌ 解析失敗，請確認格式。")

    # ==========================================
    # 📊 顯示戰情速報與表格
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
                
        # 顯示完整數據表格
        st.dataframe(df, use_container_width=True)
