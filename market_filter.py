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
