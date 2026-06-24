import streamlit as st
import yfinance as yf
import pandas as pd
import base64
import json
from datetime import datetime, timedelta

def run_grid_search(target_date):
    """
    V29 升級版：戰情快照驗證引擎 (Out-of-Sample Forward Testing)
    取代舊有的全市場網格搜索，改為驗證「過去的戰情包」至今的真實戰果。
    """
    st.markdown("### ⏳ V29 戰情快照驗證引擎")
    st.info("請在下方貼上您過去某日儲存的「Base64 戰情壓縮包」，系統將自動追蹤至今的真實戰果。")

    import_str = st.text_area("📥 貼上歷史戰情壓縮包 (Base64 代碼)", height=100)
    
    if st.button("🚀 啟動時光機軌跡追蹤", type="primary", use_container_width=True):
        if not import_str:
            st.warning("⚠️ 請先貼上壓縮包代碼！")
            return
            
        try:
            decoded = base64.b64decode(import_str).decode()
            past_portfolio = json.loads(decoded)
        except Exception as e:
            st.error("❌ 壓縮包代碼解析失敗，請確認格式是否正確。")
            return

        if not past_portfolio:
            st.warning("⚠️ 該壓縮包內無持股資料。")
            return

        st.success(f"📦 成功載入 {len(past_portfolio)} 檔歷史標的，正在啟動 YFinance 軌跡追蹤...")
        progress_bar = st.progress(0)

        results = []
        for i, item in enumerate(past_portfolio):
            code = item.get('代號', item.get('code', ''))
            cost = float(item.get('成本價', item.get('cost', item.get('成本', 0.0))))

            if not code: continue

            try:
                # 抓取從目標日期到今天的數據
                tkr = yf.Ticker(f"{code}.TW")
                hist = tkr.history(start=target_date.strftime('%Y-%m-%d'))
                if hist.empty:
                    tkr = yf.Ticker(f"{code}.TWO")
                    hist = tkr.history(start=target_date.strftime('%Y-%m-%d'))

                if not hist.empty and len(hist) > 0:
                    highest_price = float(hist['High'].max())
                    lowest_price = float(hist['Low'].min())
                    current_price = float(hist['Close'].iloc[-1])

                    # 計算績效
                    max_profit_pct = ((highest_price - cost) / cost) * 100 if cost > 0 else 0
                    mdd_pct = ((lowest_price - highest_price) / highest_price) * 100 if highest_price > 0 else 0
                    current_ret_pct = ((current_price - cost) / cost) * 100 if cost > 0 else 0

                    # 抓取半年數據以計算目前的 MA60 季線狀態
                    hist_6mo = tkr.history(period="6mo")
                    status = "未知"
                    if not hist_6mo.empty and len(hist_6mo) >= 60:
                        ma60 = float(hist_6mo['Close'].rolling(window=60).mean().iloc[-1])
                        if current_price < ma60:
                            status = "🔴 已陣亡 (跌破季線)"
                        else:
                            status = "🟢 存活 (守住季線)"

                    results.append({
                        "代號": code,
                        "當時成本": cost,
                        "最高漲幅": f"+{max_profit_pct:.1f}%",
                        "最大回撤(MDD)": f"{mdd_pct:.1f}%",
                        "至今報酬": f"{current_ret_pct:.1f}%",
                        "V29 判定": status
                    })
            except Exception as e:
                pass

            progress_bar.progress((i + 1) / len(past_portfolio))

        if results:
            df_res = pd.DataFrame(results)
            st.markdown("### 🎯 V29 紀律驗證報告")
            st.dataframe(df_res, use_container_width=True)
            
            # 總結算
            survived = len([r for r in results if "存活" in r["V29 判定"]])
            st.info(f"**戰場總結**：當時建倉的 {len(results)} 檔標的中，若嚴格遵守 V29 季線防守紀律，目前共有 **{survived}** 檔存活。")
