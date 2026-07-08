import streamlit as st
import pandas as pd
import re

def render_sniper_module():
    st.header("🎯 主力 X 光狙擊室")
    st.markdown("請從戰情中心將目標「一鍵上膛」，並貼上籌碼明細進行 X 光解碼。")
    
    # ==========================================
    # 🎯 自動填彈系統：強制綁定 Session State (解決 Streamlit 緩存 Bug)
    # ==========================================
    # 確保中央大腦裡有這個變數，避免報錯
    if 'target_id' not in st.session_state:
        st.session_state['target_id'] = ""
        
    col1, col2 = st.columns([1, 2])
    with col1:
        # 🛡️ 終極修復：使用 key="target_id" 直接綁定中央大腦，絕對不會再漏接！
        stock_id = st.text_input("🎯 狙擊目標 (股票代號)", key="target_id")
    
    with col2:
        st.info("💡 提示：在【🔥 終極戰報】點擊「一鍵上膛」後，代號會自動填入此處。")

    # ==========================================
    # 📥 數據輸入區
    # ==========================================
    raw_data = st.text_area(
        "📥 請貼上主力分點買賣超數據 (直接從券商軟體複製貼上)：", 
        height=250, 
        placeholder="請貼上格式如：\n摩根士丹利 619 25 594\n富邦 575 4 571\n..."
    )
    
    # ==========================================
    # 🔫 狙擊解析引擎
    # ==========================================
    if st.button("🔫 啟動 X 光掃描", type="primary", use_container_width=True):
        if not stock_id:
            st.warning("⚠️ 請先輸入或上膛股票代號！")
            return
        if not raw_data.strip():
            st.warning("⚠️ 請貼上籌碼數據！")
            return
            
        with st.spinner("正在解碼主力籌碼陣型..."):
            parsed_data = []
            lines = raw_data.strip().split('\n')
            
            for line in lines:
                # 移除多餘的空白並分割
                parts = re.split(r'\s+', line.strip())
                
                # 嘗試解析常見的券商格式 (分點名稱, 買進, 賣出, 買賣超)
                if len(parts) >= 4:
                    try:
                        # 假設最後三個是數字 (買進, 賣出, 買賣超)
                        net = int(parts[-1].replace(',', ''))
                        sell = int(parts[-2].replace(',', ''))
                        buy = int(parts[-3].replace(',', ''))
                        
                        # 前面的部分合併為分點名稱
                        broker_name = " ".join(parts[:-3])
                        # 如果 broker_name 開頭是數字 (例如複製到序號 0, 1, 2)，用正則表達式去掉它
                        broker_name = re.sub(r'^\d+\s+', '', broker_name)
                        
                        parsed_data.append({
                            "分點名稱": broker_name,
                            "買進(張)": buy,
                            "賣出(張)": sell,
                            "買賣超(張)": net
                        })
                    except ValueError:
                        continue # 跳過無法解析的雜訊行
            
            if parsed_data:
                df = pd.DataFrame(parsed_data)
                # 依照買賣超排序
                df = df.sort_values(by="買賣超(張)", ascending=False).reset_index(drop=True)
                
                st.success(f"✅ 成功解碼 【{stock_id}】 的主力陣型！")
                
                # 顯示數據表格
                st.dataframe(df, use_container_width=True)
                
                # ==========================================
                # 🦅 CIO 戰情速報
                # ==========================================
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
                    
            else:
                st.error("❌ 數據解析失敗，請確認貼上的格式是否正確（需包含：分點名稱、買進、賣出、買賣超）。")
