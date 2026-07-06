import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ==========================================
# ⚡ 效能防護罩：獨立的快取資料獲取函數
# ==========================================
@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock_data(code):
    """去 Yahoo 抓取報價並計算均線，結果快取 5 分鐘 (300秒)"""
    try:
        tkr = yf.Ticker(f"{code}.TW")
        hist = tkr.history(period="4mo")
        if hist.empty:
            tkr = yf.Ticker(f"{code}.TWO")
            hist = tkr.history(period="4mo")
            
        if not hist.empty and len(hist) >= 20:
            close = float(hist['Close'].iloc[-1])
            ma5 = float(hist['Close'].rolling(window=5).mean().iloc[-1])
            ma10 = float(hist['Close'].rolling(window=10).mean().iloc[-1])
            ma20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
            
            # 處理新上市股票沒有 MA60 的問題
            if len(hist) >= 60:
                ma60 = float(hist['Close'].rolling(window=60).mean().iloc[-1])
            else:
                ma60 = ma20 # 若無季線，以月線作為終極防線
                
            return {
                "success": True,
                "close": close,
                "ma10": ma10,
                "ma20": ma20,
                "ma60": ma60
            }
        else:
            return {"success": False, "error": "⚪ 無足夠報價資料 (請確認代號)"}
    except Exception as e:
        return {"success": False, "error": "⚪ 連線失敗"}

# ==========================================
# 🛡️ 主畫面渲染函數
# ==========================================
def render_portfolio_monitor():
    st.header("🛡️ 總司令戰情儀表板 (V30 動態停利版)")
    st.caption("導入法人級【三階段動態停利】與【季線防守血條】，抱得住大波段，躲得過大洗盤！")
    
    if 'portfolio' not in st.session_state or len(st.session_state['portfolio']) == 0:
        st.info("目前沒有監控中的持股。請從左側邊欄載入戰情包，或在雷達掃描室中加入。")
        return

    total_stocks = len(st.session_state['portfolio'])
    st.markdown(f"**監控總檔數：{total_stocks} 檔**")
    
    # 建立三欄式的卡片排版
    cols = st.columns(3)
    
    for idx, item in enumerate(st.session_state['portfolio']):
        # ⚠️ 終極修復：完美相容「成本」與「成本價」等各種 JSON 欄位命名
        code = item.get('code', item.get('Ticker', item.get('代號', '')))
        name = item.get('name', item.get('Name', item.get('名稱', '')))
        cost = float(item.get('cost', item.get('Cost', item.get('成本', item.get('成本價', 0.0)))))
        
        with cols[idx % 3]:
            card_container = st.container(border=True)
            with card_container:
                # 標題動態顯示名稱
                display_title = f"### 🎯 [{code}] {name}" if name else f"### 🎯 [{code}]"
                st.markdown(display_title)
                st.write(f"建倉成本: **{cost:.2f}**")
                
                if not code:
                    st.write("⚪ 無效的股票代號")
                else:
                    # ⚡ 呼叫快取函數，瞬間取得資料 (5分鐘內不會重複連線 Yahoo)
                    data = fetch_stock_data(code)
                    
                    if data["success"]:
                        close = data["close"]
                        ma10 = data["ma10"]
                        ma20 = data["ma20"]
                        ma60 = data["ma60"]
                        
                        # 計算真實報酬率與乖離
                        ret_pct = ((close - cost) / cost) * 100 if cost > 0 else 0
                        bias_20 = ((close - ma20) / ma20) * 100
                        dist_60ma = ((close - ma60) / ma60) * 100
                        
                        # ==========================================
                        # ⚖️ V30 動態停利與鐵血停損邏輯
                        # ==========================================
                        if close < ma60 or ret_pct <= -5.0:
                            status = "☠️ 死刑撤退 (破季線或虧損達5%)"
                            st.error(status)
                        elif close < ma20:
                            status = "🛑 波段停利 (跌破月線，全面清倉)"
                            st.error(status)
                        elif bias_20 >= 15.0:
                            status = "🚨 乖離過熱 (建議減碼 1/3 放口袋)"
                            st.warning(status)
                        elif close < ma10:
                            status = "🟡 正常洗盤 (破10MA，底倉續抱)"
                            st.warning(status)
                        else:
                            status = "🟢 強勢續抱 (站穩短均線)"
                            st.success(status)
                            
                        # 顯示核心數據
                        st.metric("最新收盤", f"{close:.2f}", f"{ret_pct:.2f}%")
                        st.caption(f"月線(20MA): {ma20:.2f} | 季線(60MA): {ma60:.2f}")
                        
                        # 🛡️ 季線防守血條 (視覺化)
                        st.markdown(f"**🛡️ 距季線防守空間: `{dist_60ma:.2f}%`**")
                        
                        # 動態血條長度與顏色計算
                        hp_val = max(0.0, min(100.0, 50 + dist_60ma * 2)) # 基準50，每1%加減2
                        hp_color = "#00cc66" if dist_60ma > 0 else "#ff3333"
                        st.markdown(
                            f"""
                            <div style="width: 100%; background-color: #444444; border-radius: 5px; margin-bottom: 10px;">
                              <div style="width: {hp_val}%; height: 8px; background-color: {hp_color}; border-radius: 5px;"></div>
                            </div>
                            """, unsafe_allow_html=True
                        )
                    else:
                        st.write(data["error"])
                        
                # 刪除按鈕
                if st.button("🗑️ 撤退/刪除", key=f"del_{idx}", use_container_width=True):
                    st.session_state['portfolio'].pop(idx)
                    st.rerun()
