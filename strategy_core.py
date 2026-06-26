import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import io

try:
    from sector_dict import STOCK_SECTOR
except ImportError:
    STOCK_SECTOR = {}

def load_and_clean_csv(file):
    encodings = ['big5-hkscs', 'cp950', 'utf-8', 'utf-8-sig']
    file_bytes = file.getvalue() 
    for enc in encodings:
        try:
            text = file_bytes.decode(enc)
            lines = text.split('\n')
            header_idx = -1
            for i, line in enumerate(lines[:15]):
                if '代號' in line or '證券代號' in line:
                    header_idx = i
                    break
            if header_idx != -1:
                csv_data = '\n'.join(lines[header_idx:])
                df = pd.read_csv(io.StringIO(csv_data), dtype=str, skipinitialspace=True)
                df.columns = df.columns.str.strip().str.replace('"', '').str.replace(' ', '')
                return df
        except:
            continue
    return None

def find_column(df, keywords):
    for col in df.columns:
        for kw in keywords:
            if kw in str(col):
                return col
    return None

def add_targets_to_portfolio(selected_codes, default_cost, df):
    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = []
    for code in selected_codes:
        name = df[df['代號']==code]['名稱'].values[0]
        existing = next((item for item in st.session_state['portfolio'] if item.get("代號") == code), None)
        if existing:
            existing["成本價"] = default_cost 
        else:
            st.session_state['portfolio'].append({
                "代號": code, "名稱": name, "成本價": default_cost
            })

def run_radar(uploaded_csvs, filter_bias_max, filter_resonance, filter_vol_min):
    st.markdown("### 🧠 V29.5 終極雙腦評分雷達 (戰情簡報生成版)")
    
    if st.button("🚀 啟動雷達掃描", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("⏳ [1/3] 執行 CSV 內部迴圈：解析所有法人籌碼...")
        
        all_data = []
        for file in uploaded_csvs:
            df = load_and_clean_csv(file)
            if df is None: continue
            col_code = find_column(df, ['證券代號', '代號', 'Code'])
            col_name = find_column(df, ['證券名稱', '名稱', 'Name'])
            col_trust = find_column(df, ['投信買賣超', '投信-買賣超', '投信買超', '投信買賣超股數'])
            
            if col_code and col_trust:
                df[col_code] = df[col_code].astype(str).str.replace('=', '').str.replace('"', '').str.strip()
                df[col_trust] = pd.to_numeric(df[col_trust].astype(str).str.replace(',', ''), errors='coerce').fillna(0) / 1000.0
                temp_df = df[[col_code, col_name, col_trust]].copy()
                temp_df.columns = ['代號', '名稱', '投信買賣超']
                all_data.append(temp_df)
                
        if not all_data:
            st.error("❌ CSV 解析失敗：找不到『代號』或『投信買賣超』欄位。")
            return
            
        merged_df = pd.concat(all_data)
        merged_df['買超天數'] = (merged_df['投信買賣超'] > 0).astype(int)
        summary_df = merged_df.groupby(['代號', '名稱']).agg(
            總買超=('投信買賣超', 'sum'), 連買天數=('買超天數', 'sum')
        ).reset_index()

        top_candidates = summary_df[summary_df['總買超'] > 0].copy()
        top_candidates['所屬族群'] = top_candidates['代號'].map(lambda x: STOCK_SECTOR.get(x, "其他/未分類"))
        sector_counts = top_candidates[top_candidates['所屬族群'] != "其他/未分類"]['所屬族群'].value_counts()
        
        total_csv_stocks = len(top_candidates)
        progress_bar.progress(20)
        status_text.text(f"⏳ [2/3] 啟動 YFinance 引擎：檢驗 {total_csv_stocks} 檔標的...")
        
        results = []
        stats = {"yf_fail": 0, "vol_fail": 0, "ma60_fail": 0, "bias_max_fail": 0, "reso_fail": 0}
        
        for i, (idx, row) in enumerate(top_candidates.iterrows()):
            code = row['代號']
            if len(code) != 4: 
                stats["yf_fail"] += 1
                continue
            try:
                tkr = yf.Ticker(f"{code}.TW")
                hist = tkr.history(period="6mo")
                if hist.empty:
                    tkr = yf.Ticker(f"{code}.TWO")
                    hist = tkr.history(period="6mo")
                    
                if not hist.empty and len(hist) >= 60:
                    close = float(hist['Close'].iloc[-1])
                    ma5 = float(hist['Close'].rolling(window=5).mean().iloc[-1])
                    ma10 = float(hist['Close'].rolling(window=10).mean().iloc[-1])
                    ma20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
                    ma60 = float(hist['Close'].rolling(window=60).mean().iloc[-1])
                    
                    vol_today = float(hist['Volume'].iloc[-1]) / 1000
                    vol_5d = float(hist['Volume'].rolling(window=5).mean().iloc[-1]) / 1000 
                    if vol_5d == 0: vol_5d = 1 
                    
                    if vol_5d < filter_vol_min:
                        stats["vol_fail"] += 1
                        continue
                    if close < ma60:
                        stats["ma60_fail"] += 1
                        continue
                    
                    bias_20 = ((close - ma20) / ma20) * 100
                    if bias_20 > filter_bias_max:
                        stats["bias_max_fail"] += 1
                        continue
                        
                    sector = row['所屬族群']
                    resonance_count = sector_counts.get(sector, 1) if sector != "其他/未分類" else 1
                    if filter_resonance and resonance_count < 3:
                        stats["reso_fail"] += 1
                        continue
                    
                    trust_score = row['連買天數'] * 15
                    resonance_bonus = resonance_count * 5 
                    left_brain_score = trust_score + resonance_bonus
                    
                    right_brain_score = 0
                    rb_evidence = []
                    
                    vol_ratio = vol_today / vol_5d
                    if vol_ratio >= 3.0:
                        right_brain_score += 60
                        rb_evidence.append("爆量>3x")
                    elif vol_ratio >= 2.5:
                        right_brain_score += 50
                        rb_evidence.append("爆量>2.5x")
                    elif vol_ratio >= 1.5:
                        right_brain_score += 30
                        rb_evidence.append("出量>1.5x")
                        
                    right_brain_score += 10 
                    high_20d = float(hist['High'].rolling(window=20).max().iloc[-2])
                    if close >= high_20d:
                        right_brain_score += 10
                        rb_evidence.append("創20日高")
                        
                    abs_bias = abs(bias_20)
                    if abs_bias < 3.0:
                        right_brain_score += 20
                        rb_evidence.append("乖離<3%")
                    elif abs_bias <= 5.0:
                        right_brain_score += 10
                        rb_evidence.append("乖離3-5%")
                    elif abs_bias > 8.0:
                        right_brain_score -= 20
                        rb_evidence.append("乖離>8%")
                        
                    ma_values = [ma5, ma10, ma20]
                    entanglement = (max(ma_values) - min(ma_values)) / min(ma_values)
                    if entanglement < 0.02 and (close > ma5 > ma10 > ma20):
                        right_brain_score += 15
                        rb_evidence.append("均線糾結發散")
                    
                    total_score = left_brain_score + right_brain_score
                    display_resonance = f"{sector} ({resonance_count}檔)" if sector != "其他/未分類" else "無共振"
                    
                    if right_brain_score >= 40 and left_brain_score >= 45:
                        strategy_type = "🔥 雙腦共振 (主將)"
                    elif right_brain_score >= 40:
                        strategy_type = "🚀 動能突破 (右腦)"
                    else:
                        strategy_type = "🛡️ 籌碼防禦 (左腦)"
                    
                    results.append({
                        "代號": code, "名稱": row['名稱'], "投信總買超(張)": int(row['總買超']),
                        "連買天數": row['連買天數'], "最新收盤": round(close, 2),
                        "月線乖離(%)": round(bias_20, 2), "今日量比": round(vol_ratio, 1),
                        "🤝 族群共振": display_resonance, "🛡️ 左腦分": left_brain_score,
                        "🚀 右腦分": right_brain_score, "🔥 總分": round(total_score, 1),
                        "🎯 戰略屬性": strategy_type,
                        "🧠 右腦證據": ",".join(rb_evidence) if rb_evidence else "量縮洗盤中"
                    })
                else:
                    stats["yf_fail"] += 1
            except:
                stats["yf_fail"] += 1
            progress_bar.progress(20 + int(((i + 1) / total_csv_stocks) * 75))
            
        status_text.text("⏳ [3/3] 彙整戰情報告...")
        progress_bar.progress(100)
        status_text.empty()
        
        # 🤖 產生 AI 戰略簡報 Prompt
        top_sectors_str = ", ".join([f"{k}({v}檔)" for k, v in sector_counts.head(3).items()]) if not sector_counts.empty else "無明顯族群"
        survivors_str = ""
        for r in sorted(results, key=lambda x: x['🔥 總分'], reverse=True):
            survivors_str += f"- [{r['代號']}] {r['名稱']} (總分:{r['🔥 總分']} | 屬性:{r['🎯 戰略屬性']} | 乖離:{r['月線乖離(%)']}%)\n"
        if not survivors_str:
            survivors_str = "- 無標的存活\n"
            
        # 讀取日曆警報 (若無則顯示平靜)
        calendar_alert = st.session_state.get('calendar_alert_text', '🟢 【平靜期】目前無重大日曆事件')

        prompt_text = f"""【HIOS Wave Radar V29 戰情交接包】
請 Manus 首席軍師接收以下雷達掃描數據，並結合今日大盤風控燈號與最新聯網情報，為我進行深度戰略推演：

📅 0. 日曆風險參數：
- {calendar_alert}

📊 1. 原始籌碼熱力圖 (投信真正的主戰場)：
- 總掃描檔數：{total_csv_stocks} 檔
- 投信買超前三大族群：{top_sectors_str}

☠️ 2. 雷達擊殺報告 (市場真實的洗盤/過熱狀況)：
- 跌破季線死刑：{stats['ma60_fail']} 檔 (趨勢轉空)
- 乖離過大被殺：{stats['bias_max_fail']} 檔 (追高風險/投信結帳區)
- 流動性/無共振淘汰：{stats['vol_fail'] + stats['reso_fail']} 檔

🏆 3. 最終存活菁英 (請針對以下標的進行聯網與盈虧比分析)：
{survivors_str}
💡 總司令指示：
請先判斷上述「原始熱力圖」與「存活菁英」是否存在資金錯位？並結合目前外資空單水位，告訴我這幾檔菁英是「真建倉」還是「假突破」？給出具體的資金分配與防守建議！"""
       

        st.session_state['radar_results'] = results
        st.session_state['radar_stats'] = stats
        st.session_state['radar_total_csv'] = total_csv_stocks
        st.session_state['filter_resonance'] = filter_resonance
        st.session_state['strategy_prompt'] = prompt_text

    if 'radar_results' in st.session_state:
        results = st.session_state['radar_results']
        stats = st.session_state['radar_stats']
        total_csv_stocks = st.session_state['radar_total_csv']
        saved_filter_resonance = st.session_state.get('filter_resonance', True)
        
        with st.expander("🛠️ 雷達濾網擊殺報告 (點擊展開看真相)", expanded=False):
            st.markdown(f"**CSV 原始投信買超檔數**：`{total_csv_stocks}` 檔")
            st.markdown(f"❌ **無報價/連線失敗**：`{stats['yf_fail']}` 檔")
            st.markdown(f"❌ **流動性不足被殺**：`{stats['vol_fail']}` 檔")
            st.markdown(f"❌ **跌破季線死刑**：`{stats['ma60_fail']}` 檔")
            st.markdown(f"❌ **乖離過大被殺**：`{stats['bias_max_fail']}` 檔")
            if saved_filter_resonance:
                st.markdown(f"❌ **無族群共振被殺**：`{stats['reso_fail']}` 檔")
            st.markdown(f"✅ **最終存活真龍**：`{len(results)}` 檔")
        
        if results:
            final_df = pd.DataFrame(results).sort_values('🔥 總分', ascending=False).reset_index(drop=True)
            st.success(f"🎯 掃描完成！共篩選出 {len(final_df)} 檔符合條件的標的。")
            st.dataframe(final_df, use_container_width=True)
            
            # 🤖 新增：一鍵生成 AI 戰略簡報區塊
            st.markdown("### 🤖 一鍵生成 AI 戰略簡報")
            st.caption("💡 點擊程式碼區塊右上角的「複製」按鈕，直接貼給 Manus 進行深度戰略討論！")
            st.code(st.session_state.get('strategy_prompt', ''), language="markdown")
            
            st.markdown("### 🎯 鎖定目標：加入戰情監控")
            with st.container(border=True):
                col_sel, col_cost, col_btn = st.columns([2, 1, 1])
                with col_sel:
                    selected_codes = st.multiselect(
                        "選擇要加入監控的標的：", 
                        final_df['代號'].tolist(),
                        format_func=lambda x: f"{x} - {final_df[final_df['代號']==x]['名稱'].values[0]}"
                    )
                with col_cost:
                    default_cost = st.number_input("設定建倉成本 (若尚未買進可設為 0)", min_value=0.0, value=0.0, step=0.5)
                with col_btn:
                    st.write("") 
                    st.write("")
                    st.button(
                        "➕ 加入監控中心", 
                        type="primary", 
                        use_container_width=True,
                        on_click=add_targets_to_portfolio,
                        args=(selected_codes, default_cost, final_df)
                    )
        else:
            st.warning("⚠️ 經過嚴格的技術面與籌碼面濾網，本次沒有標的符合條件。請查看上方的「擊殺報告」了解原因。")
            if 'strategy_prompt' in st.session_state:
                st.markdown("### 🤖 一鍵生成 AI 戰略簡報")
                st.caption("💡 即使沒有標的存活，您依然可以將擊殺報告貼給 Manus，分析資金撤退方向！")
                st.code(st.session_state['strategy_prompt'], language="markdown")
