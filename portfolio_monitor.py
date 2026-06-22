import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import re

@st.cache_data(ttl=86400)
def fetch_stock_name(code):
    """使用 Yahoo 奇摩股市爬蟲抓取股名 (Title 精準解析版)"""
    try:
        url = f"https://tw.stock.yahoo.com/quote/{code}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64 ) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            # 改抓 <title> 標籤，格式通常為 "台玻(1802) - 股價走勢 - Yahoo奇摩股市"
            match = re.search(r'<title>([^<]+)</title>', res.text)
            if match:
                title_text = match.group(1)
                # 以左括號 '(' 作為切割點，精準取出前面的股名
                name = title_text.split('(')[0].strip()
                if name and "Yahoo" not in name:
                    return name
    except:
        pass
    return "自選股"

@st.cache_data(ttl=300)
def get_stock_tech(code):
    """抓取最新股價與均線 (快取 5 分鐘)"""
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
    st.header("🛡️ V27 持股監控中心 (戰情卡片版)")
    st.caption("全自動追蹤陣地，危險持股強制置頂，嚴格執行波段防守紀律。")
    
    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = []

    # --- 1. 手動新增區塊 ---
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
                        # 呼叫爬蟲抓取真實股名
                        real_name = fetch_stock_name(new_code)
                        st.session_state['portfolio'].append({
                            "代號": new_code,
                            "名稱": real_name,
                            "建倉價": new_cost,
                            "收盤價": new_cost
                        })
                        st.success(f"✅ 成功加入 {new_code} {real_name}！")
                        st.rerun()
                else:
                    st.warning("請輸入股票代號！")

    portfolio = st.session_state.get('portfolio', [])
    if not portfolio:
        st.info("💡 目前沒有持股紀錄。請在上方手動新增，或從雷達室收編真龍。")
        return

    # --- 2. 背景運算與風險排序 (危險置頂演算法) ---
    analyzed_portfolio = []
    total_cost_amt = 0.0
    total_value_amt = 0.0
    red_lights = 0
    yellow_lights = 0
    green_lights = 0

    with st.spinner("📡 正在與交易所連線，計算最新防守線..."):
        for idx, item in enumerate(portfolio):
            code = str(item.get('代號', ''))
            name = item.get('名稱', f'股票 {code}')
            cost = float(item.get('建倉價', 0.0))
            
            close, ma5, ma10, ma20 = get_stock_tech(code)
            
            # 狀態判定與給分 (分數越高越危險，排越上面)
            priority_score = 0
            status_html = ""
            ret_pct = 0.0
            
            if close is not None:
                ret_pct = ((close - cost) / cost * 100) if cost > 0 else 0
                total_cost_amt += cost
                total_value_amt += close
                
                if close < ma10:
                    priority_score = 3
                    status_html = "<span style='color:#ff3333; font-weight:bold;'>🔴 破線撤退 (跌破10MA)</span>"
                    red_lights += 1
                elif close < ma5:
                    priority_score = 2
                    status_html = "<span style='color:#ffcc00; font-weight:bold;'>🟡 警戒防守 (退守10MA)</span>"
                    yellow_lights += 1
                else:
                    priority_score = 1
                    status_html = "<span style='color:#00cc66; font-weight:bold;'>🟢 強勢續抱 (站穩5MA)</span>"
                    green_lights += 1
            else:
                priority_score = 0 # 連線失敗放最下面
                status_html = "⚪ 連線中或無報價"

            analyzed_portfolio.append({
                "idx": idx, "code": code, "name": name, "cost": cost,
                "close": close, "ma5": ma5, "ma10": ma10, "ma20": ma20,
                "ret_pct": ret_pct, "priority": priority_score, "status_html": status_html
            })

    # 依據危險程度排序 (紅燈 -> 黃燈 -> 綠燈)
    analyzed_portfolio.sort(key=lambda x: x['priority'], reverse=True)

    # --- 3. 高階投資組合儀表板 ---
    st.markdown("### 📊 總司令戰情儀表板")
    dash1, dash2, dash3, dash4 = st.columns(4)
    
    total_ret_pct = ((total_value_amt - total_cost_amt) / total_cost_amt * 100) if total_cost_amt > 0 else 0
    ret_color = "normal" if total_ret_pct == 0 else ("off" if total_ret_pct < 0 else "normal")
    
    dash1.metric("監控總檔數", f"{len(portfolio)} 檔")
    dash2.metric("整體未實現損益", f"{total_ret_pct:+.2f} %", delta_color=ret_color)
    dash3.markdown(f"<h3 style='text-align: center; color: #ff3333;'>🔴 {red_lights}</h3>", unsafe_allow_html=True)
    dash4.markdown(f"<h3 style='text-align: center; color: #00cc66;'>🟢 {green_lights}</h3>", unsafe_allow_html=True)
    
    st.markdown("---")

    # --- 4. 渲染現代化戰情卡片 ---
    for item in analyzed_portfolio:
        code = item['code']
        idx = item['idx'] 
        
        st.markdown(f"""
        <div style="border: 1px solid rgba(128, 128, 128, 0.4); border-radius: 10px; padding: 15px; margin-bottom: 15px; background-color: rgba(128, 128, 128, 0.1);">
            <h4 style="margin-top: 0; margin-bottom: 10px; color: inherit;">[{code}] {item['name']} &nbsp;&nbsp; {item['status_html']}</h4>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns([1.5, 1.5, 2, 0.5])
        
        with col1:
            new_cost = st.number_input("建倉成本", value=float(item['cost']), step=0.5, key=f"cost_{code}_{idx}")
            if new_cost != item['cost']:
                st.session_state['portfolio'][idx]['建倉價'] = new_cost
                st.rerun()
                
        with col2:
            if item['close'] is not None:
                ret_color = "#ff3333" if item['ret_pct'] < 0 else "#00cc66"
                ret_sign = "+" if item['ret_pct'] > 0 else ""
                st.markdown(f"<div style='padding-top: 8px; font-size: 18px;'>最新: <b>{item['close']:.2f}</b></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size: 18px;'>報酬: <span style='color:{ret_color}; font-weight:bold;'>{ret_sign}{item['ret_pct']:.2f}%</span></div>", unsafe_allow_html=True)
            else:
                st.warning("無報價")
                
        with col3:
            if item['close'] is not None:
                dist_5 = ((item['close'] - item['ma5']) / item['ma5']) * 100
                dist_10 = ((item['close'] - item['ma10']) / item['ma10']) * 100
                st.markdown(f"<div style='font-size: 14px;'><b>5MA (飆股線)</b>: {item['ma5']:.2f} <span style='color:#888;'>(距 {dist_5:+.1f}%)</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size: 14px;'><b>10MA (波段線)</b>: {item['ma10']:.2f} <span style='color:#888;'>(距 {dist_10:+.1f}%)</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size: 14px;'><b>20MA (大底線)</b>: {item['ma20']:.2f}</div>", unsafe_allow_html=True)
                
        with col4:
            st.write("")
            if st.button("❌", key=f"del_{code}_{idx}", help="刪除此監控"):
                st.session_state['portfolio'].pop(idx)
                st.rerun()
