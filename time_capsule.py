import streamlit as st
import pandas as pd
import os
from datetime import datetime
import yfinance as yf

CAPSULE_FILE = "time_capsules.csv"

def save_capsule(df_results, strategy_mode, min_trust, max_bias):
    """將掃描結果封裝存檔"""
    if df_results.empty:
        return False
    
    df_save = df_results.copy()
    
    # 寫入時空元數據 (Metadata)
    scan_date = datetime.now().strftime("%Y-%m-%d")
    df_save['掃描日期'] = scan_date
    df_save['策略模式'] = strategy_mode
    df_save['參數_投信下限'] = min_trust
    df_save['參數_乖離上限'] = max_bias
    
    # 重新排列欄位，讓元數據排在前面
    cols = ['掃描日期', '策略模式', '代號', '名稱', '收盤價', '總分'] + [c for c in df_save.columns if c not in ['掃描日期', '策略模式', '代號', '名稱', '收盤價', '總分']]
    df_save = df_save[cols]
    
    # 存入 CSV (如果檔案存在就附加，不存在就建立)
    if os.path.exists(CAPSULE_FILE):
        df_existing = pd.read_csv(CAPSULE_FILE)
        # 防呆機制：避免同一天、同策略重複存檔
        df_existing = df_existing[~((df_existing['掃描日期'] == scan_date) & (df_existing['策略模式'] == strategy_mode))]
        df_final = pd.concat([df_existing, df_save], ignore_index=True)
    else:
        df_final = df_save
        
    # 使用 utf-8-sig 確保 Excel 打開不會亂碼
    df_final.to_csv(CAPSULE_FILE, index=False, encoding='utf-8-sig')
    return True

def render_capsule_ui():
    """渲染時光膠囊的 UI 介面與回測邏輯"""
    st.title("⏳ 時光膠囊 (績效覆盤競技場)")
    st.markdown("在這裡，您可以喚醒過去的掃描名單，系統將自動抓取最新股價，為您計算真實的區間報酬率！")
    
    if not os.path.exists(CAPSULE_FILE):
        st.warning("⚠️ 目前還沒有任何時光膠囊！請先在「戰略雷達掃描」中執行掃描並點擊儲存。")
        return
        
    df_capsules = pd.read_csv(CAPSULE_FILE)
    
    # 選擇歷史日期與策略
    col1, col2 = st.columns(2)
    with col1:
        dates = df_capsules['掃描日期'].unique().tolist()
        dates.sort(reverse=True)
        selected_date = st.selectbox("📅 選擇覆盤日期", dates)
        
    with col2:
        df_date = df_capsules[df_capsules['掃描日期'] == selected_date]
        strategies = df_date['策略模式'].unique().tolist()
        selected_strategy = st.selectbox("🧠 選擇覆盤策略", strategies)
        
    df_show = df_date[df_date['策略模式'] == selected_strategy].copy()
    
    st.info(f"📌 當時使用的參數 ➔ 投信買超下限: {df_show['參數_投信下限'].iloc[0]} 張 | 乖離率上限: {df_show['參數_乖離上限'].iloc[0]}%")
    
    if st.button("🔄 穿越時空：計算至今真實績效"):
        with st.spinner("啟動時光機，正在聯網抓取最新股價... (請稍候)"):
            current_prices = []
            
            # 逐一抓取最新股價
            for code in df_show['代號']:
                try:
                    ticker = f"{code}.TW"
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period="1d")
                    if hist.empty:
                        ticker = f"{code}.TWO"
                        stock = yf.Ticker(ticker)
                        hist = stock.history(period="1d")
                        
                    if not hist.empty:
                        current_prices.append(round(hist['Close'].iloc[-1], 2))
                    else:
                        current_prices.append(None)
                except:
                    current_prices.append(None)
                    
            df_show['最新股價'] = current_prices
            
            # 計算區間報酬率
            df_show['區間報酬(%)'] = ((df_show['最新股價'] - df_show['收盤價']) / df_show['收盤價']) * 100
            df_show['區間報酬(%)'] = df_show['區間報酬(%)'].round(2)
            
            # 整理顯示欄位
            cols = ['代號', '名稱', '當時收盤價(建倉成本)' if c=='收盤價' else c for c in df_show.columns]
            df_show.columns = cols
            display_cols = ['代號', '名稱', '當時收盤價(建倉成本)', '最新股價', '區間報酬(%)', '總分', '戰術標籤']
            display_df = df_show[display_cols]
            
            st.success(f"✅ 成功載入 {selected_date} 的名單！以下是如果當時買進，抱到今天的真實績效：")
            
            # 顯示漸層績效表 (賺錢綠色，賠錢紅色)
            st.dataframe(
                display_df.style.background_gradient(cmap='RdYlGn', subset=['區間報酬(%)']),
                use_container_width=True, hide_index=True
            )
