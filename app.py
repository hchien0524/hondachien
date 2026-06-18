import streamlit as st
import pandas as pd
from data_engine import clean_csv_data
from strategy_core import calculate_scores
from memory_module import render_memory_module

st.set_page_config(page_title="HIOS Wave Radar V22", page_icon="🌊", layout="wide")
st.title("🌊 HIOS Wave Radar V22 (雙大腦切換版)")

# --- 側邊欄：戰術參數與記憶模組 ---
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
                
                # 根據不同模式顯示不同的漸層顏色
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
