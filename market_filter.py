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

    with col2:
        st.subheader("🇹🇼 台灣特有籌碼 (手動)")
        st.info("💡 每日盤後手動輸入，啟動抄底雷達：")
        
        col2_1, col2_2 = st.columns(2)
        with col2_1:
            foreign_oi = st.number_input("外資期貨淨未平倉 (口)", value=-70000, step=1000)
            foreign_change = st.number_input("外資單日增減 (口)", value=12000, step=500)
        with col2_2:
            margin_change = st.number_input("融資單日增減 (億)", value=-65, step=1)
            market_breadth = st.number_input("站上月線家數 (%)", min_value=0, max_value=100, value=15)
        
        if market_breadth >= 50:
            score += 1
            
        st.markdown("#### 🔍 籌碼深度解析")
        is_margin_capitulation = margin_change <= -50
        is_foreign_covering = foreign_change >= 10000
        
        # ⚠️ 關鍵連動訊號發射器：寫入 session_state
        if is_margin_capitulation and is_foreign_covering:
            st.session_state['golden_bottom'] = True
            st.error("🩸 融資單日大減超 50 億 (散戶爆發斷頭潮)")
            st.success("🐻 外資單日大舉回補超萬口 (屠刀正式放下！)")
        else:
            st.session_state['golden_bottom'] = False
            if is_margin_capitulation:
                st.error("🩸 融資單日大減超 50 億 (散戶斷頭中，但外資未收手)")
            elif is_foreign_covering:
                st.success("🐻 外資單日大舉回補超萬口 (外資收手，但融資未清乾淨)")
            else:
                st.write("⚪ 籌碼無極端異常，維持常態風控。")

    with col3:
        st.subheader("🎯 戰情室燈號判定")
        
        # ⚠️ 接收抄底訊號，強制亮起紫金燈號
        if st.session_state.get('golden_bottom', False):
            light, color, advice = "🔥 黃金抄底 (極端反轉)", "#9900ff", "【滿倉狙擊】\n\n散戶斷頭+外資回補！雷達已自動降均量至1000張，請立刻啟動掃描，無腦買進季線不死鳥！"
        elif score >= 4:
            light, color, advice = "🟢 綠燈 (順風局)", "#00cc66", "【火力全開】\n\n國內外皆順風，資金水位可達 80%~100%。積極追擊強勢突破股！"
        elif score >= 2:
            light, color, advice = "🟡 黃燈 (震盪局)", "#ffcc00", "【防禦狙擊】\n\n國內外出現分歧，資金水位降至 30%~50%。只買長線大底防禦股，嚴格要求低乖離。"
        else:
            light, color, advice = "🔴 紅燈 (逆風局)", "#ff3333", "【現金為王】\n\n全面逆風，資金水位降至 0%~10%。停止開新倉，專注於舊陣地停損與防守！"
            
        st.markdown(f"""
        <div style="background-color: {color}; padding: 20px; border-radius: 10px; text-align: center; color: white;">
            <h2 style="color: white; margin-bottom: 0;">{light}</h2>
            <h1 style="color: white; font-size: 48px; margin-top: 0;">{score} / 5 分</h1>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🛡️ 總司令行動建議")
        st.info(advice)
