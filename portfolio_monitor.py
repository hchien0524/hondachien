import streamlit as st
import yfinance as yf
import pandas as pd

@st.cache_data(ttl=300) # 5分鐘快取，極速且防封鎖
def get_stock_tech(code):
    """精準抓取單檔持股的最新報價與均線"""
    for suffix in ['.TW', '.TWO']:
        try:
            tkr = yf.Ticker(f"{code}{suffix}")
            hist = tkr.history(period="1mo")
            if not hist.empty and len(hist) >= 20:
                close = float(hist['Close'].iloc[-1])
                ma5 = float(hist['Close'].rolling(window=5).mean().iloc[-1])
                ma10 = float(hist['Close'].rolling(window=10).mean().iloc[-1])
                ma20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
                return close, ma5, ma10, ma20
        except:
            continue
    return None, None, None, None

def render_portfolio_monitor():
    st.header("🛡️ V24 持股監控中心")
    st.caption("自動追蹤您的陣地，計算動態均線防守價，並比對今日最新籌碼。")
    
    # 初始化 session_state
    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = []

    # ==========================================
    # ➕ 手動新增持股區塊 (V24.1 全新功能)
    # ==========================================
    with st.expander("➕ 手動新增持股 (非雷達選股也能監控)", expanded=True):
        col_add1, col_add2, col_add3 = st.columns([2, 2, 1])
        with col_add1:
            new_code = st.text_input("股票代號 (例如: 2458)", key="new_stock_code")
        with col_add2:
            new_cost = st.number_input("建倉成本", min_value=0.0, value=0.0, step=0.5, key="new_stock_cost")
        with col_add3:
            st.markdown("  
", unsafe_allow_html=True) # 排版對齊
            if st.button("加入監控", type="primary", use_container_width=True):
                if new_code:
                    # 檢查是否已存在
                    exists = any(str(item.get('代號', '')) == str(new_code) for item in st.session_state['portfolio'])
                    if exists:
                        st.warning(f"⚠️ {new_code} 已經在監控名單中了！")
                    else:
                        st.session_state['portfolio'].append({
                            "代號": new_code,
                            "名稱": f"自選股",
                            "建倉價": new_cost,
                            "收盤價": new_cost
                        })
                        st.success(f"✅ 成功加入 {new_code}！")
                        st.rerun() # 強制刷新畫面
                else:
                    st.warning("請輸入股票代號！")

    # 讀取時光膠囊中的持股
    portfolio = st.session_state.get('portfolio', [])
    if not portfolio:
        st.info("💡 目前沒有持股紀錄。請在上方手動新增，或從側邊欄匯入戰情包。")
        return
        
    # 讀取今天最新上傳的 CSV 籌碼 (由雷達室傳遞過來)
    chip_df = st.session_state.get('latest_chip_data', pd.DataFrame())
    
    # 確保資料格式相容
    items = portfolio if isinstance(portfolio, list) else [{"代號": k, "成本": v.get("建倉價", 0)} for k, v in portfolio.items()]

    for idx, item in enumerate(items):
        code = str(item.get('代號', ''))
        name = item.get('名稱', f'股票 {code}')
        default_cost = float(item.get('收盤價', item.get('建倉價', 0.0)))
        
        st.markdown("---")
        # 加入 col4 用來放刪除按鈕
        col1, col2, col3, col4 = st.columns([1.2, 1.5, 1.5, 0.5])
        
        # 抓取最新技術面
        close, ma5, ma10, ma20 = get_stock_tech(code)
        
        with col1:
            st.subheader(f"[{code}] {name}")
            cost = st.number_input(f"建倉成本", value=default_cost, step=0.5, key=f"cost_{code}_{idx}")
            
            # 更新 session_state 裡的成本價 (讓系統記住您的修改)
            if cost != default_cost:
                st.session_state['portfolio'][idx]['建倉價'] = cost
                st.session_state['portfolio'][idx]['收盤價'] = cost
            
            if close is not None:
                ret_pct = ((close - cost) / cost * 100) if cost > 0 else 0
                ret_color = "#ff3333" if ret_pct > 0 else "#00cc66" 
                ret_sign = "+" if ret_pct > 0 else ""
                
                st.markdown(f"### 最新價: **{close:.2f}**")
                st.markdown(f"### 報酬率: <span style='color:{ret_color}; font-weight:bold;'>{ret_sign}{ret_pct:.2f}%</span>", unsafe_allow_html=True)
            else:
                st.warning("連線中或無報價...")

        if close is None:
            with col4:
                if st.button("❌ 刪除", key=f"del_none_{code}_{idx}"):
                    st.session_state['portfolio'].pop(idx)
                    st.rerun()
            continue

        # 籌碼資料比對
        trust_buy = 0
        foreign_buy = 0
        if not chip_df.empty and '代號' in chip_df.columns:
            match = chip_df[chip_df['代號'] == code]
            if not match.empty:
                trust_buy = int(match['投信買賣超'].iloc[0])
                foreign_buy = int(match['外資買賣超'].iloc[0])

        with col2:
            st.markdown("#### 🛡️ 技術防守線")
            dist_5 = ((close - ma5) / ma5) * 100
            dist_10 = ((close - ma10) / ma10) * 100
            
            st.write(f"**5MA (飆股線)**: `{ma5:.2f}` (距離 {dist_5:+.2f}%)")
            st.write(f"**10MA (波段線)**: `{ma10:.2f}` (距離 {dist_10:+.2f}%)")
            st.write(f"**20MA (大底線)**: `{ma20:.2f}`")
            
            st.markdown("#### 🦅 今日主力動向")
            if chip_df.empty:
                st.caption("⚠️ 尚未在雷達室上傳今日 CSV")
            else:
                t_color = "#ff3333" if trust_buy > 0 else "#00cc66"
                f_color = "#ff3333" if foreign_buy > 0 else "#00cc66"
                st.markdown(f"投信: <span style='color:{t_color}; font-weight:bold;'>{trust_buy} 張</span> | 外資: <span style='color:{f_color}; font-weight:bold;'>{foreign_buy} 張</span>", unsafe_allow_html=True)

        with col3:
            st.markdown("#### 🚦 AI 戰術判定")
            if close >= ma5:
                st.success("🟢 **強勢續抱**\n\n股價穩站 5 日線之上，動能強勁！不預設高點，讓獲利自然奔跑。")
            elif close >= ma10:
                st.warning("🟡 **警戒防守 (退守 10MA)**\n\n已跌破 5 日線，短線轉弱。若投信未大賣可觀察 10 日線支撐；若跌破 10MA 請準備停利。")
            else:
                st.error("🔴 **破線撤退**\n\n已跌破 10 日波段防守線！趨勢轉弱，建議嚴格執行紀律，分批或全數獲利了結。")
                
            if trust_buy < 0:
                st.error(f"⚠️ **籌碼警報**: 投信今日賣超 {trust_buy} 張，請密切注意主力結帳風險！")
                
        with col4:
            st.markdown("  
  
", unsafe_allow_html=True)
            if st.button("❌ 刪除", key=f"del_{code}_{idx}"):
                st.session_state['portfolio'].pop(idx)
                st.rerun()
