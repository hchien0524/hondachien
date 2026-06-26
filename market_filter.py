import streamlit as st
import yfinance as yf
import pandas as pd

def fetch_macro_data():
    """自動抓取大盤與總經數據 (V30 終極備援與除錯版)"""
    data = {}
    debug_info = []
    
    tickers = {
        "TAIEX": ["^TWII", "0050.TW"],  
        "SOX": ["^SOX", "SOXX"],        
        "USDTWD": ["TWD=X"]             
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
                    break  
                else:
                    debug_info.append(f"⚠️ {name} ({symbol}) 回傳空值，準備切換備援...")
            except Exception as e:
                debug_info.append(f"❌ {name} ({symbol}) 連線錯誤: {str(e)}")
        
        if not success:
            data[name] = {"close": 0, "ma20": 0}
            
    return data, debug_info

def render_market_dashboard():
    st.markdown("---")
    st.header("🚦 V30 總體大盤風控與抄底中心")
    st.caption("結合全球總經與台灣特有籌碼，精準捕捉「融資斷頭」與「外資回補」的黃金轉折點。")
    
    macro_data, debug_info = fetch_macro_data()
    
    with st.expander("📡 檢視雷達連線狀態 (若數值為0請點此展開)"):
        for info in debug_info:
            st.write(info)
            
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    score = 0
    
    # ==========================================
    # 🌐 左欄：全球連動指標 (自動)
    # ==========================================
    with col1:
        st.subheader("🌐 全球連動指標")
        
        taiex = macro_data.get("TAIEX", {"close":0, "ma20":0})
        if taiex["close"] > 0:
            taiex_status = "🟢 站上月線" if taiex["close"] >= taiex["ma20"] else "🔴 跌破月線"
            if taiex["close"] >= taiex["ma20"]: score += 1
            st.metric("加權指數 / 台灣50", f"{taiex['close']:,.2f}", taiex_status)
        
        sox = macro_data.get("SOX", {"close":0, "ma20":0})
        if sox["close"] > 0:
            sox_status = "🟢 站上月線" if sox["close"] >= sox["ma20"] else "🔴 跌破月線"
            if sox["close"] >= sox["ma20"]: score += 1
            st.metric("費城半導體 / SOXX", f"{sox['close']:,.2f}", sox_status)
        
        twd = macro_data.get("USDTWD", {"close":0, "ma20":0})
        if twd["close"] > 0:
            twd_status = "🟢 升值/穩定" if twd["close"] <= twd["ma20"] else "🔴 貶值趨勢"
            if twd["close"] <= twd["ma20"]: score += 1
            st.metric("美元/台幣匯率", f"{twd['close']:.3f}", twd_status)

    # ==========================================
    # 🇹🇼 中欄：台灣特有籌碼 (手動輸入)
    # ==========================================
    with col2:
        st.subheader("🇹🇼 台灣特有籌碼 (手動)")
        st.caption("💡 每日盤後輸入，系統將自動判定是否出現斷頭抄底訊號")
        
        c2_1, c2_2 = st.columns(2)
        with c2_1:
            foreign_oi = st.number_input("外資期貨淨未平倉 (口)", value=-83000, step=1000)
            foreign_oi_change = st.number_input("外資單日增減 (口)", value=0, step=1000, help="正數代表回補空單/增加多單")
        with c2_2:
            margin_change = st.number_input("融資單日增減 (億)", value=0, step=5, help="負數代表散戶退場/斷頭")
            market_breadth = st.number_input("站上月線家數 (%)", min_value=0, max_value=100, value=15)
            
        if market_breadth >= 50:
            score += 1
            
        # 顯示籌碼狀態標籤
        st.markdown("##### 🔍 籌碼深度解析")
        if margin_change <= -50:
            st.error("🩸 融資單日大減超 50 億 (散戶爆發斷頭潮)")
        elif margin_change <= -30:
            st.warning("🩸 融資顯著減肥 (散戶開始退場)")
        else:
            st.info("⚖️ 融資水位無極端變化")
            
        if foreign_oi_change >= 10000:
            st.success("🐻 外資單日大舉回補超萬口 (屠刀正式放下！)")
        elif foreign_oi_change <= -5000:
            st.error("🔪 外資持續大舉加空 (殺盤動能仍在)")

    # ==========================================
    # 🎯 右欄：戰情室燈號判定 (含黃金抄底覆寫邏輯)
    # ==========================================
    with col3:
        st.subheader("🎯 戰情室燈號判定")
        
        # 觸發黃金抄底的嚴格條件：融資大減 >= 30億 且 外資回補 >= 5000口
        bottom_signal = (margin_change <= -30) and (foreign_oi_change >= 5000)
        
        if bottom_signal:
            light = "🔥 黃金抄底 (浴火重生)"
            color = "#ff00ff" # 科技紫/金色
            advice = "【史詩級反轉訊號出現】\n\n散戶斷頭與外資回補同時發生！無視大盤技術面破線，立刻啟動 V30 雷達，滿倉狙擊死守季線的「不死鳥」！"
        elif foreign_oi < -50000 and score < 3:
            light = "🔴 紅燈 (極端逆風)"
            color = "#ff3333"
            advice = "【現金為王，嚴防多殺多】\n\n外資空單壓頂且無明顯回補，大盤隨時有斷頭風險。資金水位降至 0%~10%，嚴格執行季線停損！"
        elif score >= 4:
            light = "🟢 綠燈 (順風局)"
            color = "#00cc66"
            advice = "【火力全開】\n\n國內外皆順風，資金水位可達 80%~100%。積極追擊強勢突破股！"
        elif score >= 2:
            light = "🟡 黃燈 (震盪局)"
            color = "#ffcc00"
            advice = "【防禦狙擊】\n\n國內外出現分歧，資金水位降至 30%~50%。只買長線大底防禦股，嚴格要求低乖離。"
        else:
            light = "🔴 紅燈 (逆風局)"
            color = "#ff3333"
            advice = "【現金為王】\n\n全面逆風，資金水位降至 0%~10%。停止開新倉，專注於舊陣地停損與防守！"
            
        st.markdown(f"""
        <div style="background-color: {color}; padding: 20px; border-radius: 10px; text-align: center; color: white; text-shadow: 1px 1px 2px black;">
            <h2 style="color: white; margin-bottom: 0;">{light}</h2>
            <h1 style="color: white; font-size: 36px; margin-top: 10px;">{score} / 5 分</h1>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🛡️ 總司令行動建議")
        st.info(advice)
        
    st.markdown("---")
