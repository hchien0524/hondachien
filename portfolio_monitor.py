import streamlit as st
import yfinance as yf
import pandas as pd

def render_portfolio_monitor():
    st.header("🛡️ 總司令戰情儀表板 (V28 鐵血量化版)")
    
    if 'portfolio' not in st.session_state or len(st.session_state['portfolio']) == 0:
        st.info("目前沒有監控中的持股。請從左側邊欄載入戰情包，或在此手動新增。")
        return

    total_stocks = len(st.session_state['portfolio'])
    st.markdown(f"**監控總檔數：{total_stocks} 檔**")
    
    # 建立三欄式的卡片排版
    cols = st.columns(3)
    
    for idx, item in enumerate(st.session_state['portfolio']):
        # 完美相容各種 JSON 欄位命名
        code = item.get('code', item.get('Ticker', item.get('代號', '')))
        cost = float(item.get('cost', item.get('Cost', item.get('成本', 0.0))))
        
        with cols[idx % 3]:
            card_container = st.container(border=True)
            with card_container:
                st.markdown(f"### 🎯 [{code}]")
                st.write(f"建倉成本: **{cost:.2f}**")
                
                if not code:
                    st.write("⚪ 無效的股票代號")
                    continue
                    
                try:
                    # 啟動 YFinance 雙引擎 (上市 .TW / 上櫃 .TWO)
                    tkr = yf.Ticker(f"{code}.TW")
                    hist = tkr.history(period="1mo")
                    if hist.empty:
                        tkr = yf.Ticker(f"{code}.TWO")
                        hist = tkr.history(period="1mo")
                        
                    if not hist.empty:
                        close = float(hist['Close'].iloc[-1])
                        ma5 = float(hist['Close'].rolling(window=5).mean().iloc[-1])
                        ma10 = float(hist['Close'].rolling(window=10).mean().iloc[-1])
                        ma20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
                        
                        # 計算真實報酬率
                        ret_pct = ((close - cost) / cost) * 100 if cost > 0 else 0
                        
                        # ==========================================
                        # ⚖️ V28 鐵血量化判決邏輯 (完全排除新聞干擾)
                        # ==========================================
                        if close < ma20 or ret_pct <= -5.0:
                            status = "🔴 破線撤退 (破月線或虧損達5%)"
                            st.error(status)
                        elif close < ma10:
                            status = "🟡 弱勢泥搏 (破10MA，退守月線)"
                            st.warning(status)
                        else:
                            status = "🟢 強勢續抱 (站穩短均線)"
                            st.success(status)
                            
                        # 顯示核心數據
                        st.metric("最新收盤", f"{close:.2f}", f"{ret_pct:.2f}%")
                        st.caption(f"5MA: {ma5:.2f} | 10MA: {ma10:.2f} | 20MA: {ma20:.2f}")
                        
                        # 計算距離 20MA 的空間 (防守縱深)
                        dist_20ma = ((close - ma20) / ma20) * 100
                        st.markdown(f"**距 20MA 空間: {dist_20ma:.2f}%**")
                        
                    else:
                        st.write("⚪ 無報價資料 (請確認代號是否正確)")
                except Exception as e:
                    st.write("⚪ 連線失敗")
                    
                # 刪除按鈕
                if st.button("🗑️ 撤退/刪除", key=f"del_{idx}"):
                    st.session_state['portfolio'].pop(idx)
                    st.rerun()
