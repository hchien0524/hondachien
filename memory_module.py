import streamlit as st
import json
import base64
import pandas as pd

def render_memory_module():
    """負責處理持股記憶的 UI 與加密/解密邏輯"""
    st.sidebar.markdown("---")
    st.sidebar.header("💾 戰情壓縮包 (記憶模組)")
    
    # 初始化記憶體
    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = []
        
    # 1. 新增持股區塊
    with st.sidebar.expander("➕ 新增/更新持股", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            new_code = st.text_input("代號 (如 2458)")
            new_qty = st.number_input("張數", min_value=1, step=1)
        with col2:
            new_cost = st.number_input("成本價", min_value=0.0, step=0.1)
            
        if st.button("加入陣地"):
            if new_code:
                # 檢查是否已存在，若存在則更新，否則新增
                existing = next((item for item in st.session_state['portfolio'] if item["代號"] == new_code), None)
                if existing:
                    existing["張數"] = new_qty
                    existing["成本價"] = new_cost
                else:
                    st.session_state['portfolio'].append({
                        "代號": new_code,
                        "張數": new_qty,
                        "成本價": new_cost
                    })
                st.success(f"✅ 已記錄 {new_code}")
                st.rerun()
                
    # 2. 顯示目前陣地與匯出
    if st.session_state['portfolio']:
        st.sidebar.write("🛡️ 目前陣地：")
        df_port = pd.DataFrame(st.session_state['portfolio'])
        st.sidebar.dataframe(df_port, hide_index=True)
        
        if st.sidebar.button("🗑️ 清空陣地"):
            st.session_state['portfolio'] = []
            st.rerun()
            
        # 將陣地資料轉換為 Base64 加密字串
        port_json = json.dumps(st.session_state['portfolio'])
        port_b64 = base64.b64encode(port_json.encode()).decode()
        
        st.sidebar.text_area("📤 複製您的戰情壓縮包 (請妥善保存)", value=port_b64, height=100)
        
    # 3. 匯入還原區塊
    with st.sidebar.expander("📥 匯入戰情壓縮包 (還原記憶)", expanded=False):
        import_str = st.text_area("貼上您的壓縮包代碼")
        if st.button("還原陣地"):
            try:
                decoded = base64.b64decode(import_str).decode()
                st.session_state['portfolio'] = json.loads(decoded)
                st.success("✅ 陣地還原成功！")
                st.rerun()
            except:
                st.error("❌ 代碼錯誤或損毀，還原失敗。")
