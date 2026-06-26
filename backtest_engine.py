import streamlit as st
import pandas as pd
import yfinance as yf
import json
import base64

def render_time_capsule():
    st.markdown("### ⏳ V29.5 戰情快照回測引擎 (時光膠囊)")
    st.info("💡 由於缺乏全市場歷史資料庫，本引擎採用「快照驗證法」。請貼上您過去儲存的戰情壓縮包 (Base64)，系統將自動比對當時建倉成本與今日時價，驗證 V29 季線防守邏輯的真實勝率！")
    
    b64_input = st.text_area("📥 貼上過去的戰情壓縮包 (Base64 代碼)：", height=100, help="請從左側邊欄的『記憶模組』中複製過去的戰情包代碼貼於此處。")
    
    if st.button("🚀 啟動時光機進行回測", type="primary"):
        if not b64_input:
            st.warning("⚠️ 請先貼上戰情壓縮包代碼！")
            return
            
        try:
            decoded = base64.b64decode(b64_input).decode('utf-8')
            portfolio = json.loads(decoded)
        except Exception as e:
            st.error("❌ 解析失敗，請確認代碼是否完整且為正確的 Base64 格式。")
            return
            
        if not portfolio:
            st.warning("⚠️ 戰情包為空，沒有標的可供回測！")
            return
            
        st.success(f"✅ 成功解析戰情包，共 {len(portfolio)} 檔標的。正在啟動 YFinance 雙引擎進行時價比對...")
        
        results = []
        win_count = 0
        stop_loss_count = 0
        total_return = 0.0
        
        progress_bar = st.progress(0)
        
        for i, item in enumerate(portfolio):
            # 相容各種 JSON 欄位命名
            code = item.get('代號', item.get('code', item.get('Ticker', '')))
            name = item.get('名稱', item.get('name', item.get('Name', '')))
            cost = float(item.get('成本價', item.get('cost', item.get('Cost', 0.0))))
            
            if not code or cost == 0:
                continue
                
            try:
                tkr = yf.Ticker(f"{code}.TW")
                hist = tkr.history(period="6mo")
                if hist.empty:
                    tkr = yf.Ticker(f"{code}.TWO")
                    hist = tkr.history(period="6mo")
                    
                if not hist.empty and len(hist) >= 60:
                    current_close = float(hist['Close'].iloc[-1])
                    ma60 = float(hist['Close'].rolling(window=60).mean().iloc[-1])
                    
                    # 計算真實報酬率
                    ret_pct = ((current_close - cost) / cost) * 100
                    total_return += ret_pct
                    
                    if ret_pct > 0:
                        win_count += 1
                        
                    # V29 鐵血判決邏輯
                    if current_close < ma60:
                        status = "☠️ 跌破季線 (已停損)"
                        stop_loss_count += 1
                    elif ret_pct < 0:
                        status = "🟡 帳面浮虧 (季線防守中)"
                    else:
                        status = "🟢 獲利續抱"
                        
                    results.append({
                        "代號": code,
                        "名稱": name,
                        "當時建倉成本": cost,
                        "今日收盤價": round(current_close, 2),
                        "季線位置(MA60)": round(ma60, 2),
                        "報酬率(%)": round(ret_pct, 2),
                        "當前狀態": status
                    })
            except Exception as e:
                pass
                
            progress_bar.progress((i + 1) / len(portfolio))
            
        if results:
            df_res = pd.DataFrame(results)
            avg_ret = total_return / len(results)
            win_rate = (win_count / len(results)) * 100
            
            st.markdown("---")
            st.subheader("📊 回測績效報告")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("總回測檔數", f"{len(results)} 檔")
            col2.metric("勝率 (Win Rate)", f"{win_rate:.1f}%")
            col3.metric("平均報酬率", f"{avg_ret:.2f}%")
            col4.metric("觸發季線停損", f"{stop_loss_count} 檔")
            
            # 顯示詳細報表
            st.dataframe(df_res, use_container_width=True)
        else:
            st.error("❌ 無法獲取報價資料進行回測，請確認代號是否正確。")
