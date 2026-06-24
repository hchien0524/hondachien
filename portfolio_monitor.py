import streamlit as st
import yfinance as yf
import pandas as pd

def render_portfolio_monitor():
    st.header("🛡️ 總司令戰情儀表板 (V29 雙腦協同版)")
    
    # 初始化 session_state
    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = []
        
    # ➕ V29 新增：手動部署陣地 UI
    with st.expander("➕ 手動新增 / 更新持股", expanded=False):
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        with col1:
            new_code = st.text_input("股票代號 (如 2382)", key="manual_code")
        with col2:
            new_name = st.text_input("股票名稱 (選填)", key="manual_name")
        with col3:
            new_cost = st.number_input("建倉成本", min_value=0.0, step=0.5, key="manual_cost")
        with col4:
            st.write("") 
            st.write("")
            if st.button("加入陣地", use_container_width=True):
                if new_code:
                    existing = next((item for item in st.session_state['portfolio'] if item.get("代號") == new_code), None)
                    if existing:
                        existing["成本價"] = new_cost
                        if new_name: existing["名稱"] = new_name
                        st.success(f"✅ 已更新 {new_code} 成本")
                    else:
                        st.session_state['portfolio'].append({
                            "代號": new_code,
                            "名稱": new_name if new_name else "未知",
                            "成本價": new_cost
                        })
                        st.success(f"✅ 已新增 {new_code}")
                    st.rerun()
                else:
                    st.error("請輸入代號")

    if len(st.session_state['portfolio']) == 0:
        st.info("目前沒有監控中的持股。請從雷達掃描室勾選加入，或在此手動新增。")
        return

    total_stocks = len(st.session_state['portfolio'])
    st.markdown(f"**監控總檔數：{total_stocks} 檔**")
    
    # 建立三欄式的卡片排版
    cols = st.columns(3)
    
    for idx, item in enumerate(st.session_state['portfolio']):
        code = item.get('code', item.get('Ticker', item.get('代號', '')))
        name = item.get('name', item.get('Name', item.get('名稱', '')))
        cost = float(item.get('cost', item.get('Cost', item.get('成本價', item.get('成本', 0.0)))))
        
        with cols[idx % 3]:
            card_container = st.container(border=True)
            with card_container:
                display_title = f"### 🎯 [{code}] {name}" if name else f"### 🎯 [{code}]"
                st.markdown(display_title)
                st.write(f"建倉成本: **{cost:.2f}**")
                
                if not code:
                    st.write("⚪ 無效的股票代號")
                    continue
                    
                try:
                    tkr = yf.Ticker(f"{code}.TW")
                    hist = tkr.history(period="6mo")
                    if hist.empty:
                        tkr = yf.Ticker(f"{code}.TWO")
                        hist = tkr.history(period="6mo")
                        
                    if not hist.empty and len(hist) >= 60:
                        close = float(hist['Close'].iloc[-1])
                        ma5 = float(hist['Close'].rolling(window=5).mean().iloc[-1])
                        ma10 = float(hist['Close'].rolling(window=10).mean().iloc[-1])
                        ma20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
                        ma60 = float(hist['Close'].rolling(window=60).mean().iloc[-1])
                        
                        ret_pct = ((close - cost) / cost) * 100 if cost > 0 else 0
                        
                        # 🧠 V29 雙腦協同判決邏輯
                        if close < ma60:
                            status = "🔴 季線死刑 (破MA60，無條件撤退)"
                            st.error(status)
                        elif close < ma20:
                            status = "🟡 投信洗盤 (破月線，退守季線防護傘)"
                            st.warning(status)
                        elif close < ma10:
                            status = "🟡 動能休整 (破10MA，觀察月線支撐)"
                            st.warning(status)
                        else:
                            status = "🟢 強勢主升段 (站穩短均線，抱緊獲利)"
                            st.success(status)
                            
                        st.metric("最新收盤", f"{close:.2f}", f"{ret_pct:.2f}%")
                        st.caption(f"10MA: {ma10:.2f} | 20MA: {ma20:.2f} | 60MA: {ma60:.2f}")
                        
                        dist_60ma = ((close - ma60) / ma60) * 100
                        st.markdown(f"**距季線(防守線)空間: {dist_60ma:.2f}%**")
                        
                    else:
                        st.write("⚪ 無報價資料或上市未滿一季")
                except Exception as e:
                    st.write("⚪ 連線失敗")
                    
                if st.button("🗑️ 撤退/刪除", key=f"del_{idx}"):
                    st.session_state['portfolio'].pop(idx)
                    st.rerun()
