import streamlit as st
import pandas as pd
import base64
import json

# 匯入我們拆分好的模組
try:
    from data_engine import parse_chip_csv
    from strategy_core import calculate_scores
    from time_capsule import save_capsule, render_capsule_ui
    from market_filter import render_market_dashboard
    MODULES_LOADED = True
except ImportError as e:
    MODULES_LOADED = False
    st.error(f"模組匯入失敗: {e}。請確認 data_engine.py, strategy_core.py, time_capsule.py, market_filter.py 皆已建立且在同一資料夾。")

# 設定網頁標題與寬度
st.set_page_config(page_title="HIOS Wave Radar V23", layout="wide")

def main():
    st.title("🌊 HIOS Wave Radar V23 - 雙大腦風控版")

    if not MODULES_LOADED:
        st.stop()

    # ==========================================
    # 1. 啟動大盤風控儀表板
    # ==========================================
    try:
        render_market_dashboard()
    except Exception as e:
        st.warning(f"大盤風控模組載入中或發生錯誤: {e}")

    # ==========================================
    # 2. 側邊欄：戰術參數與戰情壓縮包
    # ==========================================
    st.sidebar.header("⚙️ 戰術參數設定")
    strategy_mode = st.sidebar.radio("🧠 選擇大腦", ["雙大腦交集 (推薦)", "短波突擊大腦", "長線大底大腦"])
    min_trust_buy = st.sidebar.number_input("投信買超下限 (張)", value=100, step=50)
    max_bias = st.sidebar.number_input("MA20 乖離率上限 (%)", value=5.0, step=0.5)

    st.sidebar.markdown("---")
    st.sidebar.header("💾 戰情壓縮包 (防失憶)")
    
    # 初始化 session_state
    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = {}

    # 戰情包匯入
    import_code = st.sidebar.text_input("📥 匯入戰情包代碼 (Base64)")
    if st.sidebar.button("解碼並恢復陣地"):
        if import_code:
            try:
                decoded = base64.b64decode(import_code).decode('utf-8')
                st.session_state['portfolio'] = json.loads(decoded)
                st.sidebar.success("✅ 陣地恢復成功！")
            except:
                st.sidebar.error("❌ 代碼無效，請確認複製完整。")
                
    # 戰情包匯出
    if st.sidebar.button("📦 產生最新戰情包"):
        if st.session_state['portfolio']:
            json_str = json.dumps(st.session_state['portfolio'])
            encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
            st.sidebar.code(encoded, language="text")
            st.sidebar.info("請複製上方代碼並妥善保存。")
        else:
            st.sidebar.warning("目前沒有持股紀錄可打包。")

    # ==========================================
    # 3. 主畫面：檔案上傳與雙大腦掃描
    # ==========================================
    st.markdown("---")
    st.subheader("📂 籌碼資料匯入 (支援多選)")
    uploaded_files = st.file_uploader("請上傳三大法人 CSV 檔 (可同時選上市與上櫃)", type="csv", accept_multiple_files=True)

    if st.button("🚀 啟動雙大腦深度掃描", type="primary"):
        if not uploaded_files:
            st.warning("⚠️ 請先上傳至少一份 CSV 檔案！")
            return

        with st.spinner(f"正在深度掃描 {len(uploaded_files)} 份檔案..."):
            all_dfs = []
            for f in uploaded_files:
                df = parse_chip_csv(f)
                if df is not None and not df.empty:
                    all_dfs.append(df)

            if not all_dfs:
                st.error("❌ 找不到符合的資料，請確認 CSV 格式。")
                return

            df_clean = pd.concat(all_dfs, ignore_index=True)
            st.success(f"✅ 成功匯入籌碼資料，共保留 {len(df_clean)} 檔純血普通股。")

            # 進入雙大腦評分
            df_results = calculate_scores(df_clean, min_trust_buy, max_bias, strategy_mode)

            if not df_results.empty:
                st.markdown(f"### 🎯 掃描完成！共篩選出 {len(df_results)} 檔 S 級真龍")
                
                # 顯示漸層表格 (若 matplotlib 沒裝好則降級顯示一般表格)
                try:
                    st.dataframe(
                        df_results.style.background_gradient(cmap='RdYlGn_r', subset=['乖離率(%)'])
                                        .background_gradient(cmap='YlGn', subset=['總分']),
                        use_container_width=True, hide_index=True
                    )
                except:
                    st.dataframe(df_results, use_container_width=True, hide_index=True)

                # 儲存到時光膠囊
                save_capsule(df_results, strategy_mode)
            else:
                st.warning("⚠️ 在目前的嚴格濾網下，沒有股票符合條件。這代表目前盤勢可能不佳，建議保留現金。")

    # ==========================================
    # 4. 時光膠囊 UI
    # ==========================================
    st.markdown("---")
    render_capsule_ui()

if __name__ == "__main__":
    main()
