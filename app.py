import streamlit as st
import pandas as pd
import yfinance as yf
import json, os
from datetime import datetime as dt
import twstock

st.set_page_config(page_title="HIOS V17 主控台", layout="wide")
st.title("🚀 HIOS 量化操盤系統 V17.0 (戰術主控台)")

# --- 1. 大盤多空晴雨表 ---
@st.cache_data(ttl=3600)
def get_twii():
    try:
        df = yf.download("^TWII", period="2mo", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return float(df['Close'].iloc[-1]), float(df['Close'].rolling(20).mean().iloc[-1])
    except: return None

twii = get_twii()
if twii:
    c, m = twii
    if c > m: st.success(f"🟢 大盤晴雨表：多頭強勢 (指數 {c:.0f} > 月線 {m:.0f}) | 建議資金水位：70%~100%")
    else: st.warning(f"🟡 大盤晴雨表：震盪防守 (指數 {c:.0f} < 月線 {m:.0f}) | 建議資金水位：30%~50%")

# --- 2. 參數設定與資料匯入 ---
with st.expander("⚙️ 展開 S 級真龍濾網參數", expanded=True):
    col1, col2, col3 = st.columns(3)
    sm = col1.radio("掃描範圍", ("自選", "上市", "上櫃", "全市場"), horizontal=True)
    ti = col1.text_input("自選代號 (逗號分隔)", "2382,3413,3015,8210") if sm == "自選" else ""
    csv_file = col1.file_uploader("上傳三大法人買賣超 CSV (強烈建議)", type=['csv'])
    
    a_bias = col2.slider("MA20 乖離上限(%)", 1.0, 15.0, 5.0)
    val_limit = col2.number_input("成交值下限 (億)", 0.0, 100.0, 1.0)
    
    t_buy = col3.number_input("投信買超下限 (張)", -10000, 10000, 100)
    f_buy = col3.number_input("外資買超下限 (張)", -10000, 10000, 0)
    strict_ma = col3.checkbox("嚴格模式：均線多頭排列 (MA5>MA10>MA20)")
    
    run_btn = st.button("🚀 啟動全市場掃描", use_container_width=True)

# --- 3. 核心抓取邏輯 ---
@st.cache_data
def get_tickers(m):
    tm = "上市" if "上市" in m else "上櫃"
    return [f"{c}{'.TW' if tm=='上市' else '.TWO'}" for c,i in twstock.codes.items() if i.type=='股票' and i.market==tm and len(c)==4], {c:i.name for c,i in twstock.codes.items() if i.type=='股票' and i.market==tm and len(c)==4}

if run_btn:
    chip_data = {}
        if csv_file:
        try:
            # 自動破解 Big5 編碼與跳過多餘表頭
            try:
                cdf = pd.read_csv(csv_file, encoding='utf-8')
            except:
                csv_file.seek(0)
                cdf = pd.read_csv(csv_file, encoding='big5', skiprows=1)
                if not any('代號' in str(c) or '代碼' in str(c) for c in cdf.columns):
                    csv_file.seek(0)
                    cdf = pd.read_csv(csv_file, encoding='big5', skiprows=2)

            c_col = [c for c in cdf.columns if '代號' in c or '代碼' in c or 'Code' in c][0]
            t_col = [c for c in cdf.columns if '投信' in c][0]
            f_col = [c for c in cdf.columns if '外資' in c][0]
            
            for _, r in cdf.iterrows():
                try:
                    t_val = str(r[t_col]).replace(',', '').strip()
                    f_val = str(r[f_col]).replace(',', '').strip()
                    t_num = float(t_val) if t_val not in ['nan', '', '-'] else 0
                    f_num = float(f_val) if f_val not in ['nan', '', '-'] else 0
                    
                    # 證交所單位是「股」，若數字大於一萬，自動除以 1000 轉成「張」
                    if abs(t_num) > 10000 or abs(f_num) > 10000:
                        t_num, f_num = t_num / 1000, f_num / 1000
                        
                    chip_data[str(r[c_col]).strip()] = {"投": t_num, "外": f_num}
                except: pass
        except Exception as e: 
            st.error(f"CSV 解析失敗，請確認檔案格式。錯誤細節: {e}")

    tt, nd = [], {}
    if sm == "自選":
        for t in [x.strip() for x in ti.split(",")]:
            pc = t.split('.')[0]
            if pc in twstock.codes:
                nd[pc] = twstock.codes[pc].name
                tt.append(f"{pc}{'.TW' if twstock.codes[pc].market=='上市' else '.TWO'}")
            else: tt.append(f"{pc}.TW")
    elif sm == "全市場":
        t1, n1 = get_tickers("上市")
        t2, n2 = get_tickers("上櫃")
        tt, nd = t1+t2, {**n1, **n2}
    else: tt, nd = get_tickers(sm)

    rr, pb, st_txt = [], st.progress(0), st.empty()
    
    for i, t in enumerate(tt):
        pc = t.split('.')[0]
        st_txt.text(f"掃描中 {t} ... ({i+1}/{len(tt)})")
        try:
            df = yf.download(t, period="3mo", progress=False)
            if len(df) >= 60:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                c = float(df['Close'].iloc[-1])
                v = float(df['Volume'].iloc[-1]) / 1000
                rr.append({
                    "代號": pc, "名稱": nd.get(pc,"未知"), "收盤價": round(c,2),
                    "MA5": float(df['Close'].rolling(5).mean().iloc[-1]),
                    "MA10": float(df['Close'].rolling(10).mean().iloc[-1]),
                    "MA20": float(df['Close'].rolling(20).mean().iloc[-1]),
                    "成交值(億)": round((c * v * 1000)/100000000, 2),
                    "投信": chip_data.get(pc, {}).get("投", 0),
                    "外資": chip_data.get(pc, {}).get("外", 0)
                })
        except: pass
        pb.progress((i+1)/len(tt))
    
    st.session_state['raw_data'] = rr
    st_txt.success(f"✅ 掃描完成！共取得 {len(rr)} 檔資料。")
    
    # 📦 隱藏動作：儲存時光膠囊
    if not os.path.exists("snapshots"): os.makedirs("snapshots")
    with open(f"snapshots/{dt.now().strftime('%Y-%m-%d_%H%M')}_snapshot.json", "w", encoding="utf-8") as f: 
        json.dump(rr, f, ensure_ascii=False)

# --- 4. 戰情儀表板與 Manus 匯出 ---
if st.session_state.get('raw_data'):
    df = pd.DataFrame(st.session_state['raw_data'])
    df['乖離(%)'] = round((df['收盤價'] - df['MA20']) / df['MA20'] * 100, 2)
    
    cond = (df['收盤價'] > df['MA20']) & (df['乖離(%)'] <= a_bias) & (df['成交值(億)'] >= val_limit) & (df['投信'] >= t_buy) & (df['外資'] >= f_buy)
    if strict_ma: cond = cond & (df['MA5'] > df['MA10']) & (df['MA10'] > df['MA20'])
    
    dff = df[cond].copy()
    
    if not dff.empty:
        def calc_score(r):
            s = 50
            if r['投信'] > 0: s += min(20, int(r['投信']/100))
            if r['外資'] > 0: s += min(10, int(r['外資']/200))
            if r['MA5'] > r['MA10'] > r['MA20']: s += 10
            if r['乖離(%)'] < 3: s += 10
            return min(100, s)
        
        dff['評分'] = dff.apply(calc_score, axis=1)
        dff['星級'] = dff['評分'].apply(lambda x: '🌟' * int(x/20))
        dp = dff[['代號', '名稱', '收盤價', '評分', '星級', '乖離(%)', '成交值(億)', '投信', '外資']].sort_values('評分', ascending=False)
        
        st.markdown("### 📊 S 級真龍戰情室")
        st.dataframe(dp, use_container_width=True, hide_index=True)
        
        # --- 5. Manus 專屬一鍵匯出 ---
        st.markdown("### 🤖 Manus 聯網分析指令")
        top_n = dp.head(5)
        prompt = f"Manus 軍師，這是 HIOS 雷達今日 ({dt.now().strftime('%m/%d')}) 盤後過濾出的 Top {len(top_n)} 真龍名單，請協助我進行實戰決策：\n\n"
        for _, r in top_n.iterrows():
            prompt += f"- **{r['名稱']} ({r['代號']})**：收盤 {r['收盤價']}，評分 {r['評分']} {r['星級']}，投信買超 {r['投信']} 張，月線乖離 {r['乖離(%)']}%\n"
        prompt += "\n**請幫我聯網查詢：** 這幾檔最新的法說會展望、營收動能與近期法人籌碼動向？並建議明天 50 萬資金該優先佈局哪一檔？"
        
        st.code(prompt, language="markdown")
    else:
        st.warning("⚠️ 目前參數下沒有符合條件的股票，請嘗試放寬濾網！")
