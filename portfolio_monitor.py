import streamlit as st
import yfinance as yf
import pandas as pd

def render_portfolio_monitor():
    st.header("🛡️ 總司令戰情儀表板 (V30 旗艦視覺版)")
    
    if 'portfolio' not in st.session_state or len(st.session_state['portfolio']) == 0:
        st.info("目前沒有監控中的持股。請從左側邊欄載入戰情包，或在雷達掃描後加入。")
        return

    portfolio = st.session_state['portfolio']
    
    # ==========================================
    # 💰 總司令資產總覽 (新增功能)
    # ==========================================
    st.markdown("### 💰 總資產儀表板")
    total_cost_value = 0.0
    total_current_value = 0.0
    
    # 預先抓取報價與季線資料
    stock_data_cache = {}
    with st.spinner("📡 正在同步最新報價與季線防守數據..."):
        for item in portfolio:
            code = item.get('代號', item.get('code', ''))
            qty = float(item.get('張數', 1))
            cost = float(item.get('成本價', 0.0))
            
            if code and cost > 0:
                try:
                    tkr = yf.Ticker(f"{code}.TW")
                    hist = tkr.history(period="6mo")
                    if hist.empty:
                        tkr = yf.Ticker(f"{code}.TWO")
                        hist = tkr.history(period="6mo")
                    if not hist.empty and len(hist) >= 60:
                        close = float(hist['Close'].iloc[-1])
                        ma60 = float(hist['Close'].rolling(window=60).mean().iloc[-1])
                        stock_data_cache[code] = {"close": close, "ma60": ma60}
                        
                        total_cost_value += (cost * qty * 1000)
                        total_current_value += (close * qty * 1000)
                except:
                    pass

    # 顯示總資產數據
    if total_cost_value > 0:
        total_ret_pct = ((total_current_value - total_cost_value) / total_cost_value) * 100
        total_pnl = total_current_value - total_cost_value
        
        col_t1, col_t2, col_t3 = st.columns(3)
        col_t1.metric("總投入本金", f"${total_cost_value:,.0f}")
        col_t2.metric("目前總市值", f"${total_current_value:,.0f}")
        col_t3.metric("總未實現損益", f"${total_pnl:,.0f}", f"{total_ret_pct:.2f}%")
    
    st.markdown("---")
    st.markdown(f"**監控總檔數：{len(portfolio)} 檔**")
    
    # ==========================================
    # 🛡️ 個股防守卡片 (季線血條升級)
    # ==========================================
    cols = st.columns(3)
    for idx, item in enumerate(portfolio):
        code = item.get('代號', item.get('code', ''))
        name = item.get('名稱', item.get('name', ''))
        cost = float(item.get('成本價', 0.0))
        qty = float(item.get('張數', 1))
        
        with cols[idx % 3]:
            card_container = st.container(border=True)
            with card_container:
                st.markdown(f"### 🎯 [{code}] {name}")
                st.write(f"建倉成本: **{cost:.2f}** | 張數: **{qty}**")
                
                if code in stock_data_cache:
                    data = stock_data_cache[code]
                    close = data["close"]
                    ma60 = data["ma60"]
                    
                    ret_pct = ((close - cost) / cost) * 100 if cost > 0 else 0
                    dist_ma60 = ((close - ma60) / ma60) * 100
                    
                    st.metric("最新收盤", f"{close:.2f}", f"{ret_pct:.2f}%")
                    
                    # 🩸 季線防守血條 UI
                    st.markdown("**🛡️ 季線防守縱深 (MA60)**")
                    if dist_ma60 >= 5:
                        st.success(f"🟢 安全區 | 距季線 +{dist_ma60:.2f}%")
                    elif dist_ma60 >= 0:
                        st.warning(f"🟡 警戒區 | 距季線 +{dist_ma60:.2f}%")
                    else:
                        st.error(f"🔴 破線死刑 | 距季線 {dist_ma60:.2f}%")
                        
                    st.caption(f"季線位置: {ma60:.2f}")
                else:
                    st.write("⚪ 報價讀取中或連線失敗")
                    
                if st.button("🗑️ 撤退/刪除", key=f"del_{idx}"):
                    st.session_state['portfolio'].pop(idx)
                    st.rerun()
