import streamlit as st
import pandas as pd
from data_engine import clean_csv_data
from strategy_core import calculate_scores
from memory_module import render_memory_module
from time_capsule import save_capsule, render_capsule_ui

st.set_page_config(page_title="HIOS Wave Radar V22", page_icon="🌊", layout="wide")

# --- 側邊欄：系統導覽 ---
st.sidebar.title("🌊 HIOS 總司令面板")
app_mode = st.sidebar.radio("切換系統功能：", ["📡 戰略雷達掃描", "⏳ 時光膠囊覆盤"])
st.sidebar.markdown("---")

if app_mode == "📡 戰略雷達掃描":
    st.title("🌊 HIOS Wave Radar V22 (雙大腦切換版)")
    
    st.sidebar.header("🧠 戰略雷達模式")
    strategy_mode = st.sidebar.radio("請選擇您的作戰大腦：", ["短波段突擊 (V21.1)", "大波段翻倍 (長線)"])

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ 戰術參數設定")
    min_trust_buy = st.sidebar.number_input("投信買超下限 (張)", value=100, step=50)
    max_bias = st.sidebar.number_input("MA20 乖離率上限 (%)", value=5.0, step=0.5, help="僅適用於短波段模式")

    # 呼叫記憶模組
    render_memory_module()

    # --- 主畫面：掃描區塊 ---
    st.subheader(f"🎯 目前模式：{strategy_mode}")
    if strategy_mode == "大波段翻倍 (長線)":
        st.info("💡 大波段模式將抓取半年歷史資料，尋找季線支撐與大底突破的長線飆股。掃描時間約需 3~5 分鐘，請耐心等候。")

    uploaded_files = st.file_uploader("請上傳三大法人買賣超 CSV 檔 (可同時拖曳上市與上櫃)", type="csv", accept_multiple_files=True)

    if uploaded_files:
        if st.button(f"🚀 啟動 {strategy_mode} 掃描"):
            with st.spinner("啟動數據引擎清洗資料中..."):
                df_clean = clean_csv_data(uploaded_files)
                
            if df_clean.empty:
                st.error("⚠️ 找不到符合的資料，請確認 CSV 格式。")
            else:
                st.success(f"✅ 數據引擎運作成功！共保留 {len(df_clean)} 檔純血普通股。")
                
                with st.spinner("啟動戰略大腦計算多維度評分... (這可能需要幾分鐘)"):
                    df_results = calculate_scores(df_clean, min_trust_buy, max_bias, strategy_mode)
                    
                if df_results.empty:
                    st.warning("⚠️ 在目前的嚴格濾網下，沒有股票符合條件。")
                else:
                    st.balloons()
                    st.subheader(f"🎯 掃描完成！共篩選出 {len(df_results)} 檔 S 級真龍")
                    
                    # 暫存到 session_state，讓使用者可以決定是否存檔
                    st.session_state['latest_scan'] = df_results
                    st.session_state['latest_strategy'] = strategy_mode
                    st.session_state['latest_min_trust'] = min_trust_buy
                    st.session_state['latest_max_bias'] = max_bias
                    
                    if strategy_mode == "短波段突擊 (V21.1)":
                        st.dataframe(
                            df_results.style.background_gradient(cmap='RdYlGn_r', subset=['乖離率(%)'])
                                            .background_gradient(cmap='YlGn', subset=['總分']),
                            use_container_width=True, hide_index=True
                        )
                    else:
                        st.dataframe(
                            df_results.style.background_gradient(cmap='RdYlGn_r', subset=['底部漲幅(%)'])
                                            .background_gradient(cmap='YlGn', subset=['總分']),
                            use_container_width=True, hide_index=True
                        )
                        
    # 獨立的時光膠囊儲存按鈕
    if 'latest_scan' in st.session_state and not st.session_state['latest_scan'].empty:
        st.markdown("---")
        if st.button("💾 將本次掃描結果存入【時光膠囊】"):
            success = save_capsule(
                st.session_state['latest_scan'], 
                st.session_state['latest_strategy'],
                st.session_state['latest_min_trust'],
                st.session_state['latest_max_bias']
            )
            if success:
                st.success("✅ 成功封裝！您未來可以在左側切換到「⏳ 時光膠囊覆盤」模式，追蹤這批名單的真實績效。")

elif app_mode == "⏳ 時光膠囊覆盤":
    render_capsule_ui()
