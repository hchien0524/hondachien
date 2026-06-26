import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

def fetch_macro_data():
    """自動抓取大盤與總經數據 (V23.2 終極備援與除錯版)"""
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

def get_calendar_risk():
    """V29.5 動態日曆運算核心：精準推算結算日與季底"""
    today = datetime.date.today()
    
    # 1. 計算本月第三個星期三 (台指期結算日)
    first_day = today.replace(day=1)
    # weekday(): 0是週一, 2是週三
    days_to_first_wednesday = (2 - first_day.weekday()) % 7
    first_wednesday = first_day + datetime.timedelta(days=days_to_first_wednesday)
    third_wednesday = first_wednesday + datetime.timedelta(days=14)
    
    # 2. 判定是否為季底結帳期 (3,6,9,12月的 15號之後)
    is_quarter_end = today.month in [3, 6, 9, 12] and today.day >= 15
    
    # 3. 判定是否為結算前夕 (結算日前 6 天內，涵蓋前一週的週四到週三)
    days_to_settlement = (third_wednesday - today).days
    is_settlement_week = 0 <= days_to_settlement <= 6
    
    # 4. 戰略分級
    if is_quarter_end and is_settlement_week:
        return 3, "🚨 【雙巫日風暴】季底結帳撞上期貨結算，極端洗盤警戒！", "這是台股最凶險的時刻。法人互相踩踏，技術線型會完全失真。建議總資金水位強制降至 30% 以下，多看少做，現金為王。", "#ff3333"
    elif is_quarter_end:
        return 2, f"🔥 【投信結帳期】目前為 {today.month} 月季底，提防高檔倒貨", "投信面臨績效壓力，隨時會對高檔股獲利了結。請嚴格檢視雷達名單，乖離率 > 5% 的標的即使高分也請放棄，資金只鎖定「負乖離」的低基期股。", "#ff8c00"
    elif is_settlement_week:
        return 1, f"⚠️ 【外資控盤期】距離台指期結算 ({third_wednesday.strftime('%m/%d')}) 僅剩 {days_to_settlement} 天", "外資正在進行期貨轉倉，大盤極易出現「人為拉抬或惡意下殺」。請停止追高「右腦動能股」（極高機率是假突破），只允許在季線附近低接。", "#ffcc00"
    else:
        return 0, "🟢 【平靜期】目前無重大日曆事件", "市場回歸基本面與技術面，請依循雷達的左右腦分數正常操作。", "#00cc66"

def render_market_dashboard():
    st.markdown("---")
    st.header("🚦 V29.5 總體大盤風控中心 (含時間感知引擎)")
    st.caption("結合全球總經、法人籌碼與日曆事件，判定今日大盤天氣，提供資金水位建議。")
    
    # ==========================================
    # 📅 1. 戰情日曆警報器 (UI 渲染)
    # ==========================================
    level, title, advice, color = get_calendar_risk()
    
    # 將日曆狀態存入記憶體，供 strategy_core.py 的戰略簡報使用
    st.session_state['calendar_alert_text'] = title 
    
    if level > 0:
        st.markdown(f"""
        <div style="background-color: {color}15; border-left: 6px solid {color}; padding: 15px; border-radius: 5px; margin-bottom: 25px;">
            <h3 style="color: {color}; margin-top: 0; margin-bottom: 10px;">{title}</h3>
            <p style="margin-bottom: 0; font-size: 16px; color: #e0e0e0;"><strong>💡 戰略提示：</strong>{advice}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info(f"{title}：{advice}")

    # ==========================================
    # 🌐 2. 自動抓取數據與除錯訊息
    # ==========================================
    macro_data, debug_info = fetch_macro_data()
    
    with st.expander("📡 檢視雷達連線狀態 (若數值為0請點此展開)"):
        for info in debug_info:
            st.write(info)
            
    # ==========================================
    # 📊 3. 建立 UI 面板
    # ==========================================
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
        
        future_oi = st.number_input("外資期貨淨未平倉 (口)", value=-15000, step=1000)
        if future_oi >= -30000:
            score += 1
            st.success("🟢 外資空單水位安全")
        else:
            st.error("🔴 外資大舉佈空，警戒！")
            
        market_breadth = st.number_input("站上月線家數比例 (%)", min_value=0, max_value=100, value=55)
        if market_breadth >= 50:
            score += 1
            st.success("🟢 內部結構健康")
        else:
            st.error("🔴 內部結構轉弱 (拉積盤風險)")

    with col3:
        st.subheader("🎯 戰情室燈號判定")
        
        if score >= 4:
            light, color, advice_text = "🟢 綠燈 (順風局)", "#00cc66", "【火力全開】\n\n國內外皆順風，資金水位可達 **80%~100%**。積極追擊強勢突破股！"
        elif score >= 2:
            light, color, advice_text = "🟡 黃燈 (震盪局)", "#ffcc00", "【防禦狙擊】\n\n國內外出現分歧，資金水位降至 **30%~50%**。只買長線大底防禦股，嚴格要求低乖離。"
        else:
            light, color, advice_text = "🔴 紅燈 (逆風局)", "#ff3333", "【現金為王】\n\n全面逆風，資金水位降至 **0%~10%**。停止開新倉，專注於舊陣地停損與防守！"
            
        st.markdown(f"""
        <div style="background-color: {color}; padding: 20px; border-radius: 10px; text-align: center; color: black;">
            <h2 style="color: black; margin-bottom: 0;">{light}</h2>
            <h1 style="color: black; font-size: 48px; margin-top: 0;">{score} / 5 分</h1>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🛡️ 總司令行動建議")
        st.info(advice_text)
        
    st.markdown("---")
