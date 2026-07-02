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
    try:
        # 🌟 強制將檔案讀取游標歸零
        file.seek(0)  
        content = file.read()
        
        if not content:
            st.error(f"❌ 檔案 {file.name} 讀取為空，請嘗試重新上傳！")
            return None
            
        try:
            text = content.decode('cp950', errors='ignore')
        except Exception:
            text = content.decode('utf-8', errors='ignore')
            
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        lines = text.split('\n')
        
        # 🚀 V30.5 終極表頭鎖定：必須同時包含「代碼/代號」與「名稱」，完美避開官方標題陷阱！
        header_idx = -1
        for i, line in enumerate(lines):
            clean_line = line.replace('"', '').replace(' ', '')
            if ('代號' in clean_line or '代碼' in clean_line) and '名稱' in clean_line:
                header_idx = i
                break
                
        if header_idx == -1:
            st.error(f"❌ 檔案 {file.name} 找不到包含「代號」與「名稱」的真實表頭！")
            return None
            
        # 萬能分隔符號破解：同時支援逗號(,)與Tab(\t)
        df = pd.read_csv(io.StringIO(text), skiprows=header_idx, sep=r'[,\t]+', engine='python', on_bad_lines='skip')
        
        raw_cols = [str(c) for c in df.columns]
        df.columns = [str(c).replace('"', '').replace(' ', '').replace('\n', '').strip() for c in df.columns]
        
        for col in df.columns:
            if '代號' in col or '代碼' in col:
                df.rename(columns={col: '代號'}, inplace=True)
                break
        for col in df.columns:
            if '名稱' in col:
                df.rename(columns={col: '名稱'}, inplace=True)
                break
                
        if '代號' not in df.columns:
            st.error(f"❌ 檔案 {file.name} 找不到「代號」欄位！")
            return None
            
        # 🛡️ 排除 0 開頭 ETF 鐵門 (並處理官方 CSV 常見的 ="2330" 格式)
        df['代號'] = df['代號'].astype(str).str.replace('=', '').str.replace('"', '').str.strip()
        df = df[df['代號'].str.match(r'^[1-9]\d{3}$')]
        
        # 🛡️ 寬鬆尋標邏輯
        trust_col = None
        for c in df.columns:
            if '投信' in c and ('買賣超' in c or '買賣' in c or '差額' in c or '淨買' in c or '買超' in c):
                trust_col = c
                break
                
        if not trust_col: 
            st.error(f"❌ 檔案 {file.name} 找不到「投信買賣超」相關欄位！")
            st.warning(f"🕵️‍♂️ 系統實際讀取到的原始欄位有：{', '.join(raw_cols)}")
            return None
        
        df_clean = pd.DataFrame()
        df_clean['代號'] = df['代號']
        df_clean['名稱'] = df['名稱'] if '名稱' in df.columns else "未知"
        df_clean['投信買賣超'] = pd.to_numeric(df[trust_col].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0) / 1000
        return df_clean
    except Exception as e:
        st.error(f"❌ 解析檔案 {file.name} 時發生錯誤: {e}")
        return None

def add_to_portfolio(selected_codes, default_cost, final_df):
    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = []
    added_count = 0
    for code in selected_codes:
        existing = next((item for item in st.session_state['portfolio'] if item["代號"] == code), None)
        if not existing:
            row_data = final_df[final_df['代號'] == code].iloc[0]
            st.session_state['portfolio'].append({
                "代號": code,
                "名稱": row_data['名稱'],
                "張數": 1,
                "成本價": default_cost
            })
            added_count += 1
    if added_count > 0:
        st.toast(f"✅ 成功將 {added_count} 檔標的加入監控中心！請切換至 Tab 2 查看。")

def run_radar(uploaded_csvs, filter_bias_max, filter_resonance, filter_vol_min):
    st.markdown("### 🧠 V30 雙腦評分雷達 (戰情透視版)")
    
    if st.session_state.get('golden_bottom', False):
        original_vol = filter_vol_min
        filter_vol_min = 1000
        st.markdown(f"""
        <div style="background-color: #9900ff; padding: 15px; border-radius: 8px; color: white; margin-bottom: 20px;">
            <h4 style="color: white; margin-top: 0;">🔥 【黃金抄底模式已啟動】</h4>
            偵測到大盤極端恐慌，系統已自動將 5 日均量門檻從 <b>{original_vol} 張</b> 強制降至 <b>1000 張</b>，為您精準打撈量縮見底的真龍！
        </div>
        """, unsafe_allow_html=True)
        
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    status_text.text("⏳ [1/3] 執行 CSV 內部迴圈：解析所有法人籌碼...")
    all_data = []
    for file in uploaded_csvs:
        df = load_and_clean_csv(file)
        if df is not None:
            all_data.append(df)
            
    if not all_data:
        st.error("❌ CSV 解析失敗：找不到有效資料或格式錯誤。")
        return
        
    merged_df = pd.concat(all_data)
    merged_df['買超天數'] = (merged_df['投信買賣超'] > 0).astype(int)
    summary_df = merged_df.groupby(['代號', '名稱']).agg(
        總買超=('投信買賣超', 'sum'),
        連買天數=('買超天數', 'sum')
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
        
        hist = pd.DataFrame()
        
        try:
            tkr = yf.Ticker(f"{code}.TW")
            hist = tkr.history(period="4mo")
        except Exception:
            pass
            
        if hist.empty or len(hist) < 20:
            try:
                tkr = yf.Ticker(f"{code}.TWO")
                hist = tkr.history(period="4mo")
            except Exception:
                pass
        
        try:
            if not hist.empty and len(hist) >= 20:
                close = float(hist['Close'].iloc[-1])
                ma20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
                vol_5d = float(hist['Volume'].rolling(window=5).mean().iloc[-1]) / 1000 
                
                if len(hist) >= 60:
                    ma60 = float(hist['Close'].rolling(window=60).mean().iloc[-1])
                else:
                    ma60 = ma20
                    
                bias_20 = ((close - ma20) / ma20) * 100
                
                if vol_5d < filter_vol_min:
                    stats["vol_fail"] += 1
                    continue
                    
                if close < ma60:
                    stats["ma60_fail"] += 1
                    continue
                    
                if bias_20 > filter_bias_max:
                    stats["bias_max_fail"] += 1
                    continue
                    
                sector = row['所屬族群']
                resonance_count = sector_counts.get(sector, 1) if sector != "其他/未分類" else 1
                if filter_resonance and resonance_count < 3:
                    stats["reso_fail"] += 1
                    continue
                    
                left_score = min(row['連買天數'] * 15 + (5 - bias_20) * 3, 75)
                right_score = 30 if bias_20 < 3 else (20 if bias_20 < 5 else 0)
                if close > ma60: right_score += 10
                
                total_score = left_score + right_score
                
                if total_score >= 100 and resonance_count >= 3:
                    strategy_type = "🔥 雙腦共振 (主將)"
                elif right_score >= 40:
                    strategy_type = "🚀 動能突破 (右腦)"
                else:
                    strategy_type = "🛡️ 籌碼防禦 (左腦)"
                    
                results.append({
                    "代號": code,
                    "名稱": row['名稱'],
                    "投信總買超(張)": int(row['總買超']),
                    "連買天數": row['連買天數'],
                    "最新收盤": round(close, 2),
                    "月線乖離(%)": round(bias_20, 2),
                    "5日均量(張)": int(vol_5d),
                    "🤝 族群共振": f"{sector} ({resonance_count}檔)" if sector != "其他/未分類" else "無共振",
                    "🧠 左腦分": round(left_score, 1),
                    "⚡ 右腦分": round(right_score, 1),
                    "🔥 總分": round(total_score, 1),
                    "🎯 戰略屬性": strategy_type
                })
            else:
                stats["yf_fail"] += 1
        except Exception:
            stats["yf_fail"] += 1
            
        progress_bar.progress(20 + int(((i + 1) / total_csv_stocks) * 75))
        
    status_text.text("⏳ [3/3] 彙整戰情報告...")
    progress_bar.progress(100)
    status_text.empty()
    
    with st.expander("🛠️ 雷達濾網擊殺報告 (點擊展開看真相)", expanded=True):
        st.markdown(f"**CSV 原始純淨個股數**：`{total_csv_stocks}` 檔 (已排除 ETF)")
        st.markdown(f"❌ **無報價/連線失敗**：`{stats['yf_fail']}` 檔")
        st.markdown(f"❌ **流動性不足被殺**：`{stats['vol_fail']}` 檔 *(均量 < {filter_vol_min} 張)*")
        st.markdown(f"❌ **跌破季線死刑**：`{stats['ma60_fail']}` 檔")
        st.markdown(f"❌ **乖離過大被殺**：`{stats['bias_max_fail']}` 檔 *(乖離 > {filter_bias_max}%)*")
        if filter_resonance:
            st.markdown(f"❌ **無族群共振被殺**：`{stats['reso_fail']}` 檔")
        st.markdown(f"✅ **最終存活真龍**：`{len(results)}` 檔")
    
    if results:
        final_df = pd.DataFrame(results).sort_values('🔥 總分', ascending=False).reset_index(drop=True)
        st.success(f"🎯 掃描完成！共篩選出 {len(final_df)} 檔符合條件的標的。")
        st.dataframe(final_df, use_container_width=True)
        
        st.markdown("### 🎯 鎖定目標：加入戰情監控")
        col_sel, col_cost, col_btn = st.columns([2, 1, 1])
        with col_sel:
            selected_codes = st.multiselect("選擇要監控的標的", final_df['代號'].tolist(), format_func=lambda x: f"{x} {final_df[final_df['代號']==x]['名稱'].values[0]}")
        with col_cost:
            default_cost = st.number_input("預設建倉成本", min_value=0.0, value=0.0, step=0.5, help="加入後可至 Tab 2 修改精確成本")
        with col_btn:
            st.write("")
            st.button("➕ 加入監控中心", type="primary", use_container_width=True, on_click=add_to_portfolio, args=(selected_codes, default_cost, final_df))
    else:
        st.warning("⚠️ 經過嚴格的技術面與籌碼面濾網，本次沒有標的符合條件。請查看上方的「擊殺報告」了解原因。")
