import streamlit as st
import yfinance as yf
import pandas as pd

def fetch_macro_data():
    """自動抓取大盤與總經數據 (V23.2 終極備援與除錯版)"""
    data = {}
    debug_info = []
    
    # 建立備援機制：[主目標, 備援目標]
    # 如果 Yahoo 封鎖了指數，我們就改抓高度連動的 ETF
    tickers = {
        "TAIEX": ["^TWII", "0050.TW"],  # 台股加權 / 元大台灣50
        "SOX": ["^SOX", "SOXX"],        # 費城半導體 / 費半 ETF
        "USDTWD": ["TWD=X"]             # 美元兌台幣匯率
    }
    
    for name, symbol_list in tickers.items():
        success = False
        for symbol in symbol_list:
            try:
                tkr = yf.Ticker(symbol)
                df = tkr.history(period="2mo")
                if not df.empty and len(df) >= 20:
                    close_price = float(df['Close'].iloc[-1])
                    ma20 = float(df['Close'].rolling(window=20).mean().iloc[-1])
                    data[name] = {"close": close_price, "ma20": ma20}
                    success = True
                    debug_info.append(f"✅ {name} ({symbol}) 抓取成功！收盤價: {close_price:.2f}")
                    break  # 成功就跳出迴圈，不抓備援
                else:
                    debug_info.append(f"⚠️ {name} ({symbol}) 回傳空值，準備切換備援...")
            except Exception as e:
                debug_info.append(f"❌ {name} ({symbol}) 連線錯誤: {str(e)}")
        
        if not success:
            data[name] = {"close": 0, "ma20": 0}
            
    return data, debug_info

def render_market_dashboard():
    st.markdown("---")
    st.header("🚦 V23 總體大盤風控中心")
    st.caption("結合全球總經與法人籌碼，判定今日大盤天氣，提供資金水位建議。")
    
    # 1. 自動抓取數據與除錯訊息
    macro_data, debug_info = fetch_macro_data()
    
    # 顯示連線狀態 (幫助總司令除錯)
    with st.expander("📡 檢視雷達連線狀態 (若數值為0請點此展開)"):
        for info in debug_info:
            st.write(info)
            
    # 2. 建立 UI 面板
    col1, col2, col3 = st.columns(3)
    
    score = 0
    
    with col1:
        st.subheader("🌐 全球連動指標 (自動)")
        
        # 台股加權
        taiex = macro_data.get("TAIEX", {"close":0, "ma20":0})
        if taiex["close"] > 0:
            taiex_status = "🟢 站上月線" if taiex["close"] >= taiex["ma20"] else "🔴 跌破月線"
            if taiex["close"] >= taiex["ma20"]: score += 1
            st.metric("加權指數 / 台灣50", f"{taiex['close']:,.2f}", taiex_status)
        else:
            st.metric("加權指數 / 台灣50", "連線失敗", "請展開上方雷達狀態")
        
        # 費城半導體
        sox = macro_data.get("SOX", {"close":0, "ma20":0})
        if sox["close"] > 0:
            sox_status = "🟢 站上月線" if sox["close"] >= sox["ma20"] else "🔴 跌破月線"
            if sox["close"] >= sox["ma20"]: score += 1
            st.metric("費城半導體 / SOXX", f"{sox['close']:,.2f}", sox_status)
        else:
            st.metric("費城半導體 / SOXX", "連線失敗", "請展開上方雷達狀態")
        
        # 台幣匯率
        twd = macro_data.get("USDTWD", {"close":0, "ma20":0})
        if twd["close"] > 0:
            twd_status = "🟢 升值/穩定" if twd["close"] <= twd["ma20"] else "🔴 貶值趨勢"
            if twd["close"] <= twd["ma20"]: score += 1
            st.metric("美元/台幣匯率", f"{twd['close']:.3f}", twd_status)
        else:
            st.metric("美元/台幣匯率", "連線失敗", "請展開上方雷達狀態")

    with col2:
        st.subheader("🇹🇼 台灣特有籌碼 (手動)")
        st.info("💡 確保系統穩定，請每日盤後手動輸入以下兩項關鍵數據：")
        
        foreign_futures = st.number_input("外資期貨淨未平倉 (口)", value=-15000, step=1000)
        if foreign_futures > -25000:
            score += 1
            st.success("🟢 外資空單水位安全")
        else:
            st.error("🔴 外資大舉佈空，警戒！")
            
        market_breadth = st.slider("站上月線家數比例 (%)", min_value=0, max_value=100, value=55)
        if market_breadth >= 50:
            score += 1
            st.success("🟢 內部結構健康")
        else:
            st.error("🔴 內部結構轉弱 (拉積盤風險)")

    with col3:
        st.subheader("🎯 戰情室燈號判定")
        
        if score >= 4:
            light, color, advice = "🟢 綠燈 (順風局)", "#00cc66", "【火力全開】\n\n國內外皆順風，資金水位可達 **80%~100%**。積極追擊強勢突破股！"
        elif score >= 2:
            light, color, advice = "🟡 黃燈 (震盪局)", "#ffcc00", "【防禦狙擊】\n\n國內外出現分歧，資金水位降至 **30%~50%**。只買長線大底防禦股，嚴格要求低乖離。"
        else:
            light, color, advice = "🔴 紅燈 (逆風局)", "#ff3333", "【現金為王】\n\n全面逆風，資金水位降至 **0%~10%**。停止開新倉，專注於舊陣地停損與防守！"
            
        st.markdown(f"""
        <div style="background-color: {color}; padding: 20px; border-radius: 10px; text-align: center; color: black;">
            <h2 style="color: black; margin-bottom: 0;">{light}</h2>
            <h1 style="color: black; font-size: 48px; margin-top: 0;">{score} / 5 分</h1>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🛡️ 總司令行動建議")
        st.info(advice)
        
    st.markdown("---")
