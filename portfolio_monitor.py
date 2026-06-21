import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import re

@st.cache_data(ttl=86400)
def fetch_stock_name(code):
    """終極正名系統：FinMind + Yahoo奇摩股市爬蟲雙備援"""
    # 1. 先嘗試 FinMind (若額度恢復則秒抓)
    try:
        url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInfo&data_id={code}"
        res = requests.get(url, timeout=2 )
        if res.status_code == 200:
            data = res.json().get('data', [])
            if len(data) > 0:
                name = data[0].get('stock_name', '').strip()
                if name: return name
    except:
        pass

    # 2. FinMind 罷工時，啟動 Yahoo 奇摩股市網頁爬蟲 (無 API 限制)
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        url = f"https://tw.stock.yahoo.com/quote/{code}"
        res = requests.get(url, headers=headers, timeout=3 )
        if res.status_code == 200:
            # 尋找標題格式： <title>義隆(2458) - 股價走勢 - Yahoo奇摩股市</title>
            match = re.search(r'<title>(.*?)\(\d+\)', res.text)
            if match:
                name = match.group(1).strip()
                if name: return name
    except:
        pass
        
    return f"股票 {code}"

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
    st.header("🛡️ V26 持股監控中心 (高階戰情版)")
    st.caption("自動追蹤陣地，計算動態均線防守價，並將【危險持股】強制置頂！")
    
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
                            "名稱": "", # 留空讓下方邏輯自動抓取
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
    # 1. 預先抓取資料與計算狀態 (為了排序與儀表板)
    # ==========================================
    processed_data = []
    total_cost_amt = 0.0
    total_value_amt = 0.0
    red_lights = 0
    
    chip_df = st.session_state.get('latest_chip_data', pd.DataFrame())

    with st.spinner("📡 正在與交易所連線，同步最新防守線與股名..."):
        for item in portfolio:
            code = str(item.get('代號', ''))
            name = item.get('名稱', '')
            cost = float(item.get('建倉價', item.get('收盤價', 0.0)))
            
            # 【新增】自動正名邏輯 (解決只有代號沒有股名的問題)
            if not name or name == '自選股' or name.startswith('股票'):
                found = False
                if not chip_df.empty and '代號' in chip_df.columns:
                    match = chip_df[chip_df['代號'] == code]
                    if not match.empty and '名稱' in match.columns:
                        name = str(match['名稱'].iloc[0])
                        found = True
                if not found:
                    name = fetch_stock_name(code)
                item['名稱'] = name # 更新回 session_state 讓他永遠記住
            
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
            
            # 🚨 狀態判定
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
                
            # 籌碼判定
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
    # 3. 危險持股置頂排序與渲染
    # ==========================================
    # 排序邏輯：先排危險度 (紅>黃>綠)，同燈號再排報酬率 (賠越多的越上面)
    processed_data.sort(key=lambda x: (x['status_score'], -x['ret_pct']), reverse=True)

    st.markdown("---")
    st.subheader("📋 持股防守明細 (危險度排序)")

    for item in processed_data:
        code = item['code']
        
        with st.container():
            # 標題與燈號
            st.markdown(f"""
            <div style="border-left: 6px solid {item['color']}; padding-left: 15px; margin-bottom: 15px; background-color: rgba(255,255,255,0.03); border-radius: 5px; padding-top: 5px; padding-bottom: 5px;">
                <h4 style="margin-bottom: 0;">[{code}] {item['name']} <span style="font-size: 18px; color: {item['color']}; margin-left: 10px;"> {item['status_text']}</span></h4>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns([1.5, 1.5, 1.5, 0.5])
            
            with col1:
                new_cost = st.number_input("建倉成本", value=float(item['cost']), step=0.5, key=f"cost_{code}")
                if new_cost != item['cost']:
                    for p in st.session_state['portfolio']:
                        if str(p['代號']) == code:
                            p['建倉價'] = new_cost
                            p['收盤價'] = new_cost
                    st.rerun()
                
                if item['close'] > 0:
                    ret_color = "#ff3333" if item['ret_pct'] < 0 else "#00cc66"
                    ret_sign = "+" if item['ret_pct'] > 0 else ""
                    st.markdown(f"最新價: **{item['close']:.2f}**")
                    st.markdown(f"報酬率: <span style='color:{ret_color}; font-weight:bold; font-size:18px;'>{ret_sign}{item['ret_pct']:.2f}%</span>", unsafe_allow_html=True)
                else:
                    st.warning("無報價")

            with col2:
                if item['close'] > 0:
                    dist_5 = ((item['close'] - item['ma5']) / item['ma5']) * 100
                    dist_10 = ((item['close'] - item['ma10']) / item['ma10']) * 100
                    
                    st.write(f"**5MA (飆股線)**: `{item['ma5']:.2f}` (距 {dist_5:+.1f}%)")
                    st.write(f"**10MA (波段線)**: `{item['ma10']:.2f}` (距 {dist_10:+.1f}%)")
                    st.write(f"**20MA (大底線)**: `{item['ma20']:.2f}`")

            with col3:
                st.markdown("**🦅 主力動向 (近1日)**")
                trust_buy = item.get('trust_buy', 0)
                if trust_buy != 0:
                    t_color = "#ff3333" if trust_buy < 0 else "#00cc66"
                    st.markdown(f"投信: <span style='color:{t_color}; font-weight:bold;'>{trust_buy} 張</span>", unsafe_allow_html=True)
                    if trust_buy < 0:
                        st.error("⚠️ 投信賣超，注意結帳！")
                else:
                    st.caption("無最新籌碼資料")
                    
                # 💡 獲利保本戰術提示
                if item['ret_pct'] > 5 and item['status_score'] == 1:
                    st.info("💡 獲利已拉開，建議將防守線設為成本價，確保不敗！")

            with col4:
                st.write("")
                st.write("")
                if st.button("❌ 刪除", key=f"del_{code}"):
                    st.session_state['portfolio'] = [p for p in st.session_state['portfolio'] if str(p['代號']) != code]
                    st.rerun()
                    
        st.markdown("---")
