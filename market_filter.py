import streamlit as st
import yfinance as yf
import pandas as pd

@st.cache_data(ttl=3600) # 快取 1 小時，避免頻繁請求 API
def fetch_macro_data():
    """自動抓取大盤與總經數據"""
    data = {}
    tickers = {
        "TAIEX": "^TWII",  # 台股加權指數
        "SOX": "^SOX",     # 費城半導體指數
        "USDTWD": "TWD=X"  # 美元兌台幣匯率
    }
    
    for name, ticker in tickers.items():
        try:
            df = yf.download(ticker, period="2mo", progress=False)
            if not df.empty:
                # 取得最新收盤價與 MA20
                close_price = float(df['Close'].iloc[-1])
                ma20 = float(df['Close'].rolling(window=20).mean().iloc[-1])
                data[name] = {"close": close_price, "ma20": ma20}
            else:
                data[name] = {"close": 0, "ma20": 0}
        except Exception as e:
            data[name] = {"close": 0, "ma20": 0}
            
    return data

def render_market_dashboard():
    st.markdown("---")
    st.header("🚦 V23 總體大盤風控中心")
    st.caption("結合全球總經與法人籌碼，判定今日大盤天氣，提供資金水位建議。")
    
    # 1. 自動抓取數據
    macro_data = fetch_macro_data()
    
    # 2. 建立 UI 面板
    col1, col2, col3 = st.columns(3)
    
    score = 0
    
    with col1:
        st.subheader("🌐 全球連動指標 (自動)")
        
        # 台股加權
        taiex = macro_data.get("TAIEX", {"close":0, "ma20":0})
        taiex_status = "🟢 站上月線" if taiex["close"] >= taiex["ma20"] else "🔴 跌破月線"
        if taiex["close"] >= taiex["ma20"]: score += 1
        st.metric("加權指數 (TAIEX)", f"{taiex['close']:.2f}", taiex_status)
        
        # 費城半導體
        sox = macro_data.get("SOX", {"close":0, "ma20":0})
        sox_status = "🟢 站上月線" if sox["close"] >= sox["ma20"] else "🔴 跌破月線"
        if sox["close"] >= sox["ma20"]: score += 1
        st.metric("費城半導體 (SOX)", f"{sox['close']:.2f}", sox_status)
        
        # 台幣匯率 (注意：USD/TWD 下跌代表台幣升值，為利多)
        twd = macro_data.get("USDTWD", {"close":0, "ma20":0})
        twd_status = "🟢 升值/穩定" if twd["close"] <= twd["ma20"] else "🔴 貶值趨勢"
        if twd["close"] <= twd["ma20"]: score += 1
        st.metric("美元/台幣匯率", f"{twd['close']:.3f}", twd_status)

    with col2:
        st.subheader("🇹🇼 台灣特有籌碼 (手動)")
        st.info("💡 確保系統穩定，請每日盤後手動輸入以下兩項關鍵數據：")
        
        # 外資期貨空單
        foreign_futures = st.number_input("外資期貨淨未平倉 (口)", value=-15000, step=1000, 
                                        help="輸入負數代表空單。若空單少於 25,000 口視為安全。")
        if foreign_futures > -25000:
            score += 1
            st.success("🟢 外資空單水位安全")
        else:
            st.error("🔴 外資大舉佈空，警戒！")
            
        # 站上月線家數比例
        market_breadth = st.slider("站上月線家數比例 (%)", min_value=0, max_value=100, value=55, 
                                 help="大於 50% 代表多頭結構健康。")
        if market_breadth >= 50:
            score += 1
            st.success("🟢 內部結構健康")
        else:
            st.error("🔴 內部結構轉弱 (拉積盤風險)")

    with col3:
        st.subheader("🎯 戰情室燈號判定")
        
        # 燈號邏輯判定
        if score >= 4:
            light = "🟢 綠燈 (順風局)"
            advice = "【火力全開】\n\n國內外皆順風，資金水位可達 **80%~100%**。積極追擊強勢突破股！"
            color = "#00cc66"
        elif score >= 2:
            light = "🟡 黃燈 (震盪局)"
            advice = "【防禦狙擊】\n\n國內外出現分歧，資金水位降至 **30%~50%**。只買長線大底防禦股，嚴格要求低乖離。"
            color = "#ffcc00"
        else:
            light = "🔴 紅燈 (逆風局)"
            advice = "【現金為王】\n\n全面逆風，資金水位降至 **0%~10%**。停止開新倉，專注於舊陣地停損與防守！"
            color = "#ff3333"
            
        st.markdown(f"""
        <div style="background-color: {color}; padding: 20px; border-radius: 10px; text-align: center; color: black;">
            <h2 style="color: black; margin-bottom: 0;">{light}</h2>
            <h1 style="color: black; font-size: 48px; margin-top: 0;">{score} / 5 分</h1>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🛡️ 總司令行動建議")
        st.info(advice)
        
    st.markdown("---")
