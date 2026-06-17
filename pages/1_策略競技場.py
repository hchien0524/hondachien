import streamlit as st
import pandas as pd
import json, os
import yfinance as yf
import twstock

st.set_page_config(page_title="策略競技場", layout="wide")
st.title("🏟️ 策略競技場 (時光膠囊績效追蹤)")

# 檢查是否有歷史快照
if not os.path.exists("snapshots") or not os.listdir("snapshots"):
    st.warning("⚠️ 目前還沒有任何時光膠囊！請先在「主控台」執行一次全市場掃描。")
else:
    files = sorted(os.listdir("snapshots"), reverse=True)
    sel_file = st.selectbox("📂 選擇歷史快照 (掃描紀錄)", files)

    with st.expander("⚙️ 設定當時的篩選條件 (重現歷史名單)", expanded=True):
        col1, col2 = st.columns(2)
        a_bias = col1.slider("當時的 MA20 乖離上限(%)", 1.0, 15.0, 5.0)
        t_buy = col2.number_input("當時的投信買超下限 (張)", -10000, 10000, 100)

    if st.button("📊 結算此策略至今績效", use_container_width=True):
        with st.spinner("正在穿越時空，比對最新報價..."):
            # 讀取歷史快照
            with open(f"snapshots/{sel_file}", "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            
            df = pd.DataFrame(raw_data)
            
            # 套用篩選條件，還原當時的名單
            cond = (df['收盤價'] > df['MA20']) & (((df['收盤價'] - df['MA20'])/df['MA20']*100) <= a_bias) & (df['投信'] >= t_buy)
            dff = df[cond].copy()

            if dff.empty:
                st.warning("這個快照在這些條件下，沒有選出任何股票。請放寬條件！")
            else:
                dff['當時價格'] = dff['收盤價']
                dff['最新價格'] = 0.0
                
                # 逐一抓取最新報價來結算
                st_txt = st.empty()
                for i, row in dff.iterrows():
                    pc = str(row['代號'])
                    st_txt.text(f"正在結算 {pc} {row['名稱']} 的最新績效...")
                    t_suffix = f"{pc}{'.TW' if pc in twstock.codes and twstock.codes[pc].market=='上市' else '.TWO'}"
                    try:
                        cp = float(yf.Ticker(t_suffix).history(period="1d")['Close'].iloc[-1])
                        dff.at[i, '最新價格'] = round(cp, 2)
                    except:
                        dff.at[i, '最新價格'] = row['當時價格'] # 若抓不到則以原價計算
                st_txt.empty()

                # 計算報酬率
                dff['報酬率(%)'] = round((dff['最新價格'] - dff['當時價格']) / dff['當時價格'] * 100, 2)
                
                # 戰情報告總結
                win_rate = len(dff[dff['報酬率(%)'] > 0]) / len(dff) * 100
                avg_ret = dff['報酬率(%)'].mean()

                st.markdown(f"### 🎯 策略結算報告 (共 {len(dff)} 檔)")
                st.success(f"🏆 **策略勝率：{win_rate:.1f}%** │ 📈 **平均報酬率：{avg_ret:.2f}%**")

                # 顯示明細
                res_df = dff[['代號', '名稱', '當時價格', '最新價格', '報酬率(%)', '投信']].sort_values('報酬率(%)', ascending=False)
                st.dataframe(res_df, use_container_width=True, hide_index=True)
