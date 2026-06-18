import streamlit as st
import pandas as pd
from data_engine import clean_csv_data
from strategy_core import calculate_scores

st.set_page_config(page_title="HIOS Wave Radar V21", page_icon="🌊", layout="wide")
st.title("🌊 HIOS Wave Radar V21 (模組化核心版)")

st.sidebar.header("⚙️ 戰術參數設定")
min_trust_buy = st.sidebar.number_input("投信買超下限 (張)", value=100, step=50)
max_bias = st.sidebar.number_input("MA20 乖離率上限 (%)", value=5.0, step=0.5)

# --- API 直連區塊 ---
st.subheader("🌐 1. 啟動全市場掃描 (API 直連)")
if st.button("⚡️ 一鍵抓取最新籌碼 (API)"):
    st.warning("⚠️ 雲端 IP 目前遭證交所防火牆阻擋。請使用下方的 CSV 備用方案！(未來將於 V21.5 導入第三方 API 解決此問題)")

st.markdown("---")

# --- CSV 備用區塊 ---
st.subheader("📥 2. 匯入籌碼資料 (CSV 備用方案)")
uploaded_files = st.file_uploader("請上傳三大法人買賣超 CSV 檔 (可同時拖曳上市與上櫃)", type="csv", accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 啟動 V21 模組化掃描"):
        with st.spinner("啟動數據引擎清洗資料中..."):
            df_clean = clean_csv_data(uploaded_files)
            
        if df_clean.empty:
            st.error("⚠️ 找不到符合的資料，請確認 CSV 格式。")
        else:
            st.success(f"✅ 數據引擎運作成功！共保留 {len(df_clean)} 檔純血普通股。")
            
            with st.spinner("啟動戰略大腦計算多維度評分... (這可能需要幾分鐘)"):
                df_results = calculate_scores(df_clean, min_trust_buy, max_bias)
                
            if df_results.empty:
                st.warning("⚠️ 在目前的嚴格濾網下，沒有股票符合條件。")
            else:
                st.balloons()
                st.subheader(f"🎯 掃描完成！共篩選出 {len(df_results)} 檔 S 級真龍")
                st.dataframe(
                    df_results.style.background_gradient(cmap='RdYlGn_r', subset=['乖離率(%)'])
                                    .background_gradient(cmap='YlGn', subset=['總分']),
                    use_container_width=True, hide_index=True
                )
