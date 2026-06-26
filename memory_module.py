import streamlit as st
import json
import base64
import pandas as pd

def render_memory_module():
    """負責處理持股記憶的 UI，支援 JSON 檔案與 Base64 雙引擎"""
    st.sidebar.markdown("---")
    st.sidebar.header("💾 戰情壓縮包 (記憶模組)")
    
    # 初始化記憶體
    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = []
        
    # ==========================================
    # 1. 手動新增持股區塊
    # ==========================================
    with st.sidebar.expander("➕ 手動新增/更新持股", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            new_code = st.text_input("代號 (如 2458)")
            new_qty = st.number_input("張數", min_value=1, step=1)
        with col2:
            new_cost = st.number_input("成本價", min_value=0.0, step=0.1)
            
        if st.button("加入陣地"):
            if new_code:
                # 容錯處理：使用 .get() 避免舊版 JSON 缺少欄位導致當機
                existing = next((item for item in st.session_state['portfolio'] if item.get("代號", item.get("code")) == new_code), None)
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
                
    # ==========================================
    # 2. 顯示目前陣地與雙引擎匯出 (JSON 下載 + Base64)
    # ==========================================
    if st.session_state['portfolio']:
        st.sidebar.write("🛡️ 目前陣地：")
        df_port = pd.DataFrame(st.session_state['portfolio'])
        st.sidebar.dataframe(df_port, hide_index=True)
        
        if st.sidebar.button("🗑️ 清空陣地"):
            st.session_state['portfolio'] = []
            st.rerun()
            
        # 產生 JSON 字串
        port_json = json.dumps(st.session_state['portfolio'], ensure_ascii=False, indent=2)
        
        # 引擎 A：JSON 檔案下載按鈕 (長期備份用)
        st.sidebar.download_button(
            label="⬇️ 下載戰情包 (.json)",
            data=port_json,
            file_name="portfolio_backup.json",
            mime="application/json",
            use_container_width=True
        )
        
        # 引擎 B：Base64 代碼產生器 (時光機專用)
        port_b64 = base64.b64encode(port_json.encode('utf-8')).decode('utf-8')
        st.sidebar.text_area("📤 複製 Base64 代碼 (供時光機回測用)", value=port_b64, height=100)
        
    # ==========================================
    # 3. 匯入還原區塊 (支援 JSON 上傳 & Base64 貼上)
    # ==========================================
    with st.sidebar.expander("📥 還原陣地 (載入舊戰情)", expanded=False):
        
        # 選項 A: 上傳 JSON 檔案
        uploaded_file = st.file_uploader("📂 上傳 .json 戰情包", type=['json'])
        if uploaded_file is not None:
            try:
                loaded_data = json.load(uploaded_file)
                if st.button("⚠️ 確認載入 JSON (將覆蓋目前陣地)", type="primary", use_container_width=True):
                    st.session_state['portfolio'] = loaded_data
                    st.success("✅ JSON 戰情包載入成功！")
                    st.rerun()
            except Exception as e:
                st.error("檔案解析失敗，請確認是否為正確的 JSON 檔。")
        
        st.markdown("---")
        
        # 選項 B: 貼上 Base64 代碼
        import_str = st.text_area("或貼上 Base64 壓縮代碼")
        if st.button("還原 Base64 陣地", use_container_width=True):
            if import_str:
                try:
                    decoded = base64.b64decode(import_str).decode('utf-8')
                    st.session_state['portfolio'] = json.loads(decoded)
                    st.success("✅ Base64 陣地還原成功！")
                    st.rerun()
                except:
                    st.error("❌ 代碼錯誤或損毀，還原失敗。")
