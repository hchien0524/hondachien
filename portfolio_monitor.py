import streamlit as st
import yfinance as yf
import pandas as pd

def render_portfolio_monitor():
    st.header("🛡️ 總司令戰情儀表板 (V29 雙腦協同版)")
    
    if 'portfolio' not in st.session_state or len(st.session_state['portfolio']) == 0:
        st.info("目前沒有監控中的持股。請從左側邊欄載入戰情包，或在此手動新增。")
        return

    total_stocks = len(st.session_state['portfolio'])
    st.markdown(f"**監控總檔數：{total_stocks} 檔**")
    
    # 建立三欄式的卡片排版
    cols = st.columns(3)
    
    for idx, item in enumerate(st.session_state['portfolio']):
        # 完美相容各種 JSON 欄位命名，並加入 name 讀取
        code = item.get('code', item.get('Ticker', item.get('代號', '')))
        name = item.get('name', item.get('Name', item.get('名稱', '')))
        cost = float(item.get('cost', item.get('Cost', item.get('成本', 0.0))))
        
        with cols[idx % 3]:
            card_container = st.container(border=True)
            with card_container:
                # 標題動態顯示名稱
                display_title = f"### 🎯 [{code}] {name}" if name else f"### 🎯 [{code}]"
                st.markdown(display_title)
                st.write(f"建倉成本: **{cost:.2f}**")
                
                if not code:
                    st.write("⚪ 無效的股票代號")
                    continue
                    
                try:
                    # ⚠️ 軍師修正：啟動 YFinance 雙引擎，並將視野擴展至 6mo 以計算季線
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
                        ma60 = float(hist['Close'].rolling(window=60).mean().iloc[-1]) # 新增季線
                        
                        # 計算真實報酬率
                        ret_pct = ((close - cost) / cost) * 100 if cost > 0 else 0
                        
                        # ==========================================
                        # 🧠 V29 雙腦協同判決邏輯 (建倉防守與動能停利脫鉤)
                        # ==========================================
                        if close < ma60:
                            # 跌破季線，大人棄守，無條件死刑
                            status = "🔴 季線死刑 (破MA60，無條件撤退)"
                            st.error(status)
                        elif close < ma20:
                            # 跌破月線但守住季線，判定為左腦建倉洗盤期
                            status = "🟡 投信洗盤 (破月線，退守季線防護傘)"
                            st.warning(status)
                        elif close < ma10:
                            # 跌破10日線，動能休整
                            status = "🟡 動能休整 (破10MA，觀察月線支撐)"
                            st.warning(status)
                        else:
                            # 站穩短均線，右腦主升段
                            status = "🟢 強勢主升段 (站穩短均線，抱緊獲利)"
                            st.success(status)
                            
                        # 顯示核心數據
                        st.metric("最新收盤", f"{close:.2f}", f"{ret_pct:.2f}%")
                        st.caption(f"10MA: {ma10:.2f} | 20MA: {ma20:.2f} | 60MA: {ma60:.2f}")
                        
                        # 計算距離 MA60 的空間 (真正的防守縱深)
                        dist_60ma = ((close - ma60) / ma60) * 100
                        st.markdown(f"**距季線(防守線)空間: {dist_60ma:.2f}%**")
                        
                    else:
                        st.write("⚪ 無報價資料或上市未滿一季")
                except Exception as e:
                    st.write("⚪ 連線失敗")
                    
                # 刪除按鈕
                if st.button("🗑️ 撤退/刪除", key=f"del_{idx}"):
                    st.session_state['portfolio'].pop(idx)
                    st.rerun()
