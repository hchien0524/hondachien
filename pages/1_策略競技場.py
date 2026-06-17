import streamlit as st
import pandas as pd
import yfinance as yf
import json, os, glob

st.set_page_config(page_title="策略競技場", layout="wide")
st.title("📊 策略競技場 (時光機回測中心)")

if not os.path.exists("snapshots"): os.makedirs("snapshots")
files = glob.glob("snapshots/*.json")

if not files:
    st.info("💡 目前還沒有歷史快照。請先去「主控台」執行一次掃描，系統就會自動為您存下時光膠囊！")
else:
    sel_file = st.selectbox("⏳ 選擇歷史時光膠囊", sorted(files, reverse=True))
    
    with open(sel_file, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    
    st.success(f"✅ 成功載入快照！當時全市場共有 {len(raw_data)} 檔股票資料。")
    
    st.markdown("### 🎛️ 上帝視角：調整歷史參數")
    c1, c2, c3 = st.columns(3)
    a_bias = c1.slider("當時 MA20 乖離上限(%)", 1.0, 15.0, 5.0)
    val_limit = c2.number_input("當時成交值下限 (億)", 0.0, 100.0, 1.0)
    t_buy = c3.number_input("當時投信買超下限 (張)", -10000, 10000, 100)
    
    if st.button("⚔️ 啟動無情結算 (計算至今報酬率)"):
        df = pd.DataFrame(raw_data)
        df['乖離(%)'] = round((df['收盤價'] - df['MA20']) / df['MA20'] * 100, 2)
        cond = (df['收盤價'] > df['MA20']) & (df['乖離(%)'] <= a_bias) & (df['成交值(億)'] >= val_limit) & (df['投信'] >= t_buy)
        dff = df[cond].copy()
        
        if dff.empty: st.warning("這個嚴格參數下，當時沒有選出任何股票。")
        else:
            rr, pb = [], st.progress(0)
            for i, r in dff.iterrows():
                try:
                    hist = yf.download(f"{r['代號']}.TW", period="1mo", progress=False)
                    if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.get_level_values(0)
                    now_price = float(hist['Close'].iloc[-1])
                    ret = round((now_price - r['收盤價']) / r['收盤價'] * 100, 2)
                    rr.append({"代號": r['代號'], "名稱": r['名稱'], "當時買價": r['收盤價'], "今日最新價": round(now_price,2), "報酬率(%)": ret})
                except: pass
                pb.progress((i+1)/len(dff))
            
            res_df = pd.DataFrame(rr)
            win_rate = len(res_df[res_df['報酬率(%)'] > 0]) / len(res_df) * 100
            avg_ret = res_df['報酬率(%)'].mean()
            
            st.markdown("### 🏆 結算報告")
            m1, m2, m3 = st.columns(3)
            m1.metric("選出檔數", f"{len(res_df)} 檔")
            m2.metric("🎯 歷史勝率", f"{win_rate:.1f}%")
            m3.metric("💰 平均報酬率", f"{avg_ret:.2f}%")
            st.dataframe(res_df.sort_values('報酬率(%)', ascending=False), use_container_width=True, hide_index=True)
