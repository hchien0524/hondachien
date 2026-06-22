import streamlit as st
import yfinance as yf
import pandas as pd
import requests

@st.cache_data(ttl=86400)
def build_stock_mapping():
    """終極正名系統：直接抓取政府官方開放資料"""
    mapping = {}
    try:
        res_twse = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", timeout=5 )
        if res_twse.status_code == 200:
            for item in res_twse.json():
                mapping[str(item.get('Code'))] = str(item.get('Name'))
    except:
        pass
    try:
        res_tpex = requests.get("https://www.tpex.org.tw/openapi/v1/t187ap03_O", timeout=5 )
        if res_tpex.status_code == 200:
            for item in res_tpex.json():
                mapping[str(item.get('公司代號'))] = str(item.get('公司簡稱'))
    except:
        pass
    return mapping

@st.cache_data(ttl=300)
def get_stock_tech(code):
    """抓取最新報價與動態均線"""
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
    st.header("🛡️ V26.1 持股監控中心 (現代卡片版)")
    st.caption("全自動追蹤陣地，沉浸式戰情卡片，危險持股強制置頂！")
    
    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = []

    # ➕ 手動新增區塊
    with st.expander("➕ 手動新增持股 (非雷達選股也能監控)", expanded=False):
        col_add1, col_add2, col_add3 = st.columns([2, 2, 1])
        with col_add1:
            new_code = st.text_input("股票代號 (例如: 2458)", key="new_stock_code")
        with col_add2:
            new_cost = st.number_input("建倉成本", min_value=0.0, value=0.0, step=0.5, key="new_stock_cost")
        with col_add3:
            st.write("") 
            st.write("") 
            if st.button("加入監控", type="primary", use_container_width=True):
                if new_code:
                    exists = any(str(item.get('代號', '')) == str(new_code) for item in st.session_state['portfolio'])
                    if exists:
                        st.warning(f"⚠️ {new_code} 已經在監控名單中了！")
                    else:
                        st.session_state['portfolio'].append({
                            "代號": new_code,
                            "名稱": "", 
                            "建倉價": new_cost,
                            "收盤價": new_cost
                        })
                        st.success(f"✅ 成功加入 {new_code}！")
                        st.rerun()
                else:
                    st.warning("請輸入股票代號！")

    portfolio = st.session_state.get('portfolio', [])
    if not portfolio:
        st.info("💡 目前沒有持股紀錄。請在上方手動新增，或從「雷達掃描室」勾選收編。")
        return

    # ==========================================
    # 1. 預先抓取資料與計算狀態
    # ==========================================
    processed_data = []
    total_cost_amt = 0.0
    total_value_amt = 0.0
    red_lights = 0
    
    chip_df = st.session_state.get('latest_chip_data', pd.DataFrame())
    stock_dict = build_stock_mapping()

    with st.spinner("📡 正在與交易所連線，同步最新防守線與戰情卡片..."):
        for item in portfolio:
            code = str(item.get('代號', ''))
            name = item.get('名稱', '')
            cost = float(item.get('建倉價', item.get('收盤價', 0.0)))
            
            if not name or name == '自選股' or name.startswith('股票'):
                found = False
                if not chip_df.empty and '代號' in chip_df.columns:
                    match = chip_df[chip_df['代號'] == code]
                    if not match.empty and '名稱' in match.columns:
                        name = str(match['名稱'].iloc[0])
                        found = True
                if not found:
                    name = stock_dict.get(code, f"股票 {code}")
                item['名稱'] = name 
            
            close, ma5, ma10, ma20 = get_stock_tech(code)
            
            if close is None:
                processed_data.append({
                    'code': code, 'name': name, 'cost': cost, 'close': 0, 
                    'ma5': 0, 'ma10': 0, 'ma20': 0, 'ret_pct': 0, 
                    'status_score': -1, 'status_text': '連線失敗', 'color': 'gray'
                })
                continue
                
            ret_pct = ((close - cost) / cost * 100) if cost > 0 else 0
            total_cost_amt += cost 
            total_value_amt += close
            
            if close < ma10:
                status_score = 3
                status_text = "🔴 破線撤退 (跌破10MA)"
                color = "#ff3333"
                red_lights += 1
            elif close < ma5:
                status_score = 2
                status_text = "🟡 警戒防守 (跌破5MA)"
                color = "#ffcc00"
            else:
                status_score = 1
                status_text = "🟢 強勢續抱 (站穩5MA)"
                color = "#00cc66"
                
            trust_buy = 0
            if not chip_df.empty and '代號' in chip_df.columns:
                match = chip_df[chip_df['代號'] == code]
                if not match.empty:
                    trust_buy = int(match['投信買賣超'].iloc[0])
                    
            processed_data.append({
                'code': code, 'name': name, 'cost': cost, 'close': close, 
                'ma5': ma5, 'ma10': ma10, 'ma20': ma20, 'ret_pct': ret_pct, 
                'status_score': status_score, 'status_text': status_text, 
                'color': color, 'trust_buy': trust_buy
            })

    # ==========================================
    # 2. 高階戰情儀表板
    # ==========================================
    st.markdown("---")
    st.subheader("📊 總司令戰情儀表板")
    m1, m2, m3, m4 = st.columns(4)
    
    total_ret_pct = ((total_value_amt - total_cost_amt) / total_cost_amt * 100) if total_cost_amt > 0 else 0
    
    m1.metric("總持股檔數", f"{len(portfolio)} 檔")
    m2.metric("整體未實現報酬", f"{total_ret_pct:.2f} %")
    m3.metric("🔴 危險警報 (破10MA)", f"{red_lights} 檔")
    
    if red_lights > 0:
        m4.error("⚠️ 請優先處理紅燈持股！")
    else:
        m4.success("✅ 陣地安全，無破線持股。")

    # ==========================================
    # 3. 🃏 現代化戰情卡片渲染 (危險度排序)
    # ==========================================
    processed_data.sort(key=lambda x: (x['status_score'], -x['ret_pct']), reverse=True)

    st.markdown("---")
    st.subheader("📋 持股防守卡片 (危險度置頂)")

    for item in processed_data:
        code = item['code']
        
        # 使用 Streamlit 原生帶邊框的容器創造「卡片感」
        with st.container(border=True):
            
            # --- 卡片頭部 (Header) ---
            st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h3 style="margin: 0; padding: 0; border-left: 5px solid {item['color']}; padding-left: 10px;">
                        [{code}] {item['name']}
                    </h3>
                    <span style="background-color: {item['color']}15; color: {item['color']}; border: 1px solid {item['color']}; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 14px;">
                        {item['status_text']}
                    </span>
                </div>
            """, unsafe_allow_html=True)
            
            # --- 卡片身體 (Body) ---
            col1, col2, col3 = st.columns([1.2, 1.5, 1])
            
            with col1:
                new_cost = st.number_input("建倉成本", value=float(item['cost']), step=0.5, key=f"cost_{code}")
                if new_cost != item['cost']:
                    for p in st.session_state['portfolio']:
                        if str(p['代號']) == code:
                            p['建倉價'] = new_cost
                            p['收盤價'] = new_cost
                    st.rerun()
                
                if item['close'] > 0:
                    # 使用 st.metric 創造大數字視覺衝擊
                    st.metric(label="最新報價", value=f"{item['close']:.2f}", delta=f"{item['ret_pct']:.2f}%")
                else:
                    st.warning("無報價")

            with col2:
                if item['close'] > 0:
                    dist_5 = ((item['close'] - item['ma5']) / item['ma5']) * 100
                    dist_10 = ((item['close'] - item['ma10']) / item['ma10']) * 100
                    
                    st.markdown("<div style='font-size: 14px; color: gray; margin-bottom: 5px;'>📉 動態防守線</div>", unsafe_allow_html=True)
                    st.markdown(f"**5MA (飆股線)**: `{item['ma5']:.2f}` <span style='color:gray; font-size:13px;'>(距 {dist_5:+.1f}%)</span>", unsafe_allow_html=True)
                    st.markdown(f"**10MA (波段線)**: `{item['ma10']:.2f}` <span style='color:gray; font-size:13px;'>(距 {dist_10:+.1f}%)</span>", unsafe_allow_html=True)
                    st.markdown(f"**20MA (大底線)**: `{item['ma20']:.2f}`", unsafe_allow_html=True)

            with col3:
                st.markdown("<div style='font-size: 14px; color: gray; margin-bottom: 5px;'>🦅 主力動向 (近1日)</div>", unsafe_allow_html=True)
                trust_buy = item.get('trust_buy', 0)
                if trust_buy != 0:
                    t_color = "#ff3333" if trust_buy < 0 else "#00cc66"
                    st.markdown(f"投信: <span style='color:{t_color}; font-weight:bold; font-size:16px;'>{trust_buy} 張</span>", unsafe_allow_html=True)
                    if trust_buy < 0:
                        st.error("⚠️ 投信賣超結帳！")
                else:
                    st.caption("無最新籌碼資料")
                
                st.write("") # 排版微調
                if st.button("❌ 撤退平倉", key=f"del_{code}", use_container_width=True):
                    st.session_state['portfolio'] = [p for p in st.session_state['portfolio'] if str(p['代號']) != code]
                    st.rerun()
