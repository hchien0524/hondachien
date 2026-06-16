import json, os, requests, time
from datetime import datetime as dt
import streamlit as st
import yfinance as yf
import pandas as pd
import twstock as tw
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="HIOS V16.2", layout="wide")
page = st.sidebar.radio("模組", ["雷達", "競技場", "K線"])

def get_n(c): return tw.codes[c].name if c in tw.codes else "未知"
if page == "雷達":
    st.title("🚀 HIOS 波段雷達 (V16.2 全市場雙引擎)")
    if 'rd' not in st.session_state:
        try:
            with open("c.json",'r') as f:
                d=json.load(f)
                st.session_state['rd'], st.session_state['lu'] = d['d'], d['t']
        except: st.session_state['rd'], st.session_state['lu'] = [], "無"

    @st.cache_data
    def get_t(m):
        tm = "上市" if "上市" in m else "上櫃"
        return [f"{c}{'.TW' if tm=='上市' else '.TWO'}" for c,i in tw.codes.items() if i.type=='股票' and i.market==tm and len(c)==4], {c:i.name for c,i in tw.codes.items() if i.type=='股票' and i.market==tm and len(c)==4}

    st.sidebar.info(f"💾 更新: {st.session_state['lu']}")
    sm = st.sidebar.radio("範圍", ("自選","上市","上櫃","全市場"))
    ti = st.sidebar.text_area("自選代號","2382,3413") if sm=="自選" else ""
    cs = st.sidebar.radio("籌碼", ("CSV","API"))
    uc = st.sidebar.file_uploader("CSV",type=["csv"]) if cs=="CSV" else None

    if st.sidebar.button("🚀 抓取"):
        cd = {}
        if uc:
            df = pd.read_csv(uc)
            cc, fc, ic = df.columns[0], df.columns[df.columns.str.contains('外資')][0], df.columns[df.columns.str.contains('投信')][0]
            for _,r in df.iterrows(): cd[str(r[cc]).replace('=','').replace('"','').strip()] = {"外":pd.to_numeric(str(r[fc]).replace(',',''),errors='coerce')or 0, "投":pd.to_numeric(str(r[ic]).replace(',',''),errors='coerce')or 0}
        elif cs == "API":
            try:
                for i in requests.get("https://openapi.twse.com.tw/v1/fund/T86_ALL",timeout=5 ).json(): cd[str(i.get('Code','')).strip()] = {"外":float(str(i.get('ForeignInvestorDifference','0')).replace(',',''))/1000, "投":float(str(i.get('InvestmentTrustDifference','0')).replace(',',''))/1000}
                for i in requests.get("https://www.tpex.org.tw/openapi/v1/t112sb0eb",timeout=5 ).json():
                    c = str(i.get('SecuritiesCompanyCode','')).strip()
                    if c not in cd: cd[c] = {"外":0,"投":0}
                    cd[c]["外"] = float(str(i.get('Difference','0')).replace(',',''))/1000
                for i in requests.get("https://www.tpex.org.tw/openapi/v1/t112sb0ec",timeout=5 ).json():
                    c = str(i.get('SecuritiesCompanyCode','')).strip()
                    if c not in cd: cd[c] = {"外":0,"投":0}
                    cd[c]["投"] = float(str(i.get('Difference','0')).replace(',',''))/1000
            except: pass

        tt, nd = [], {}
        if sm == "自選":
            for t in [x.strip() for x in ti.split(",")]:
                pc = t.split('.')[0]
                if pc in tw.codes:
                    nd[pc] = tw.codes[pc].name
                    tt.append(f"{pc}{'.TW' if tw.codes[pc].market=='上市' else '.TWO'}")
                else: tt.append(f"{pc}.TW")
        elif sm == "全市場":
            t1, n1 = get_t("上市")
            t2, n2 = get_t("上櫃")
            tt, nd = t1+t2, {**n1, **n2}
        else: tt, nd = get_t(sm)

        rr, pb, st_txt = [], st.progress(0), st.empty()
        for i, t in enumerate(tt):
            pc = t.split('.')[0]
            st_txt.text(f"下載 {t} ... ({i+1}/{len(tt)})")
            try:
                df = yf.download(t, period="6mo", progress=False)
                if len(df) >= 60:
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    df['M20'], df['M60'], df['V'] = df['Close'].rolling(20).mean(), df['Close'].rolling(60).mean(), df['Volume']/1000
                    l = df.iloc[-1]
                    rr.append({"代號":pc, "名稱":nd.get(pc,"未知"), "收盤價":round(float(l['Close']),1), "MA20":float(l['M20']), "MA60":float(l['M60']), "成交量":int(l['V']), "5日均量":float(df['V'].rolling(5).mean().iloc[-1]), "投信":cd.get(pc,{}).get("投",0), "外資":cd.get(pc,{}).get("外",0)})
            except: pass
            pb.progress((i+1)/len(tt))
        
        st.session_state['rd'], st.session_state['lu'] = rr, dt.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open("c.json",'w') as f: json.dump({'t':st.session_state['lu'],'d':rr}, f)
        except: pass
        st_txt.success(f"✅ 完成！存入 {len(rr)} 檔。")

    if st.session_state['rd']:
        df = pd.DataFrame(st.session_state['rd'])
        with st.expander("⚙️ 參數設定", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            a20 = c1.slider("A策略 MA20 乖離(%)", 1.0, 15.0, 5.0)
            b60 = c2.slider("B策略 MA60 乖離(%)", 1.0, 20.0, 10.0)
            bv = c3.slider("B策略 成交量(張)", 500, 10000, 3000)
            mi = c4.number_input("投信買超大於", -10000, 10000, 100)

        df['A'] = (df['收盤價']>df['MA20']) & (((df['收盤價']-df['MA20'])/df['MA20']*100)<a20)
        df['B'] = (df['成交量']>df['5日均量']) & (df['成交量']>bv) & (((df['收盤價']-df['MA60'])/df['MA60']*100)<b60)
        dff = df[(df['A']|df['B']) & (df['投信']>=mi)].copy()

        if not dff.empty:
            dff['策略'] = dff.apply(lambda x: " + ".join([s for s,c in zip(["🟢 A","🔥 B"],[x['A'],x['B']]) if c]), axis=1)
            dff['乖離(%)'] = round((dff['收盤價']-dff['MA20'])/dff['MA20']*100, 1)
            dff['買區'] = dff['MA20'].apply(lambda x: f"{x:.1f}~{x*1.02:.1f}")
            dff['停損'] = round(dff['MA20']*0.97, 1)
            dp = dff[['代號','名稱','收盤價','策略','投信','外資','乖離(%)','成交量','買區','停損']].sort_values("投信", ascending=False)
            
            m1, m2, m3 = st.columns(3)
            m1.metric("🎯 總數", f"{len(dp)} 檔")
            m2.metric("🔥 投信冠軍", f"{dp.iloc[0]['名稱']}", f"{int(dp.iloc[0]['投信'])} 張")
            m3.metric("📈 最高乖離", f"{dp['乖離(%)'].max()}%")
            
            st.dataframe(dp, use_container_width=True, hide_index=True, column_config={"投信": st.column_config.ProgressColumn("投信", format="%d", min_value=0, max_value=int(dp['投信'].max()) if dp['投信'].max()>0 else 1000)})
            
            sn = st.text_input("快照命名", f"{dt.now().strftime('%Y%m%d_%H%M%S')}_名單")
            if st.button("💾 儲存快照"):
                sd = {}
                try:
                    with open("s.json","r") as f: sd=json.load(f)
                except: pass
                sd[sn] = {"d": dt.now().strftime("%Y-%m-%d %H:%M:%S"), "p": {"A乖離":a20,"B乖離":b60,"B量":bv,"投信":mi}, "r": dp[['代號','名稱','收盤價','策略']].to_dict('records')}
                with open("s.json","w") as f: json.dump(sd, f, ensure_ascii=False)
                st.success("✅ 儲存成功！")
        else: st.warning("⚠️ 無符合股票")
if page == "雷達":
    st.title("🚀 HIOS 波段雷達 (V16.2 全市場雙引擎)")
    if 'rd' not in st.session_state:
        try:
            with open("c.json",'r') as f:
                d=json.load(f)
                st.session_state['rd'], st.session_state['lu'] = d['d'], d['t']
        except: st.session_state['rd'], st.session_state['lu'] = [], "無"

    @st.cache_data
    def get_t(m):
        tm = "上市" if "上市" in m else "上櫃"
        return [f"{c}{'.TW' if tm=='上市' else '.TWO'}" for c,i in tw.codes.items() if i.type=='股票' and i.market==tm and len(c)==4], {c:i.name for c,i in tw.codes.items() if i.type=='股票' and i.market==tm and len(c)==4}

    st.sidebar.info(f"💾 更新: {st.session_state['lu']}")
    sm = st.sidebar.radio("範圍", ("自選","上市","上櫃","全市場"))
    ti = st.sidebar.text_area("自選代號","2382,3413") if sm=="自選" else ""
    cs = st.sidebar.radio("籌碼", ("CSV","API"))
    uc = st.sidebar.file_uploader("CSV",type=["csv"]) if cs=="CSV" else None

    if st.sidebar.button("🚀 抓取"):
        cd = {}
        if uc:
            df = pd.read_csv(uc)
            cc, fc, ic = df.columns[0], df.columns[df.columns.str.contains('外資')][0], df.columns[df.columns.str.contains('投信')][0]
            for _,r in df.iterrows(): cd[str(r[cc]).replace('=','').replace('"','').strip()] = {"外":pd.to_numeric(str(r[fc]).replace(',',''),errors='coerce')or 0, "投":pd.to_numeric(str(r[ic]).replace(',',''),errors='coerce')or 0}
        elif cs == "API":
            try:
                for i in requests.get("https://openapi.twse.com.tw/v1/fund/T86_ALL",timeout=5 ).json(): cd[str(i.get('Code','')).strip()] = {"外":float(str(i.get('ForeignInvestorDifference','0')).replace(',',''))/1000, "投":float(str(i.get('InvestmentTrustDifference','0')).replace(',',''))/1000}
                for i in requests.get("https://www.tpex.org.tw/openapi/v1/t112sb0eb",timeout=5 ).json():
                    c = str(i.get('SecuritiesCompanyCode','')).strip()
                    if c not in cd: cd[c] = {"外":0,"投":0}
                    cd[c]["外"] = float(str(i.get('Difference','0')).replace(',',''))/1000
                for i in requests.get("https://www.tpex.org.tw/openapi/v1/t112sb0ec",timeout=5 ).json():
                    c = str(i.get('SecuritiesCompanyCode','')).strip()
                    if c not in cd: cd[c] = {"外":0,"投":0}
                    cd[c]["投"] = float(str(i.get('Difference','0')).replace(',',''))/1000
            except: pass

        tt, nd = [], {}
        if sm == "自選":
            for t in [x.strip() for x in ti.split(",")]:
                pc = t.split('.')[0]
                if pc in tw.codes:
                    nd[pc] = tw.codes[pc].name
                    tt.append(f"{pc}{'.TW' if tw.codes[pc].market=='上市' else '.TWO'}")
                else: tt.append(f"{pc}.TW")
        elif sm == "全市場":
            t1, n1 = get_t("上市")
            t2, n2 = get_t("上櫃")
            tt, nd = t1+t2, {**n1, **n2}
        else: tt, nd = get_t(sm)

        rr, pb, st_txt = [], st.progress(0), st.empty()
        for i, t in enumerate(tt):
            pc = t.split('.')[0]
            st_txt.text(f"下載 {t} ... ({i+1}/{len(tt)})")
            try:
                df = yf.download(t, period="6mo", progress=False)
                if len(df) >= 60:
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    df['M20'], df['M60'], df['V'] = df['Close'].rolling(20).mean(), df['Close'].rolling(60).mean(), df['Volume']/1000
                    l = df.iloc[-1]
                    rr.append({"代號":pc, "名稱":nd.get(pc,"未知"), "收盤價":round(float(l['Close']),1), "MA20":float(l['M20']), "MA60":float(l['M60']), "成交量":int(l['V']), "5日均量":float(df['V'].rolling(5).mean().iloc[-1]), "投信":cd.get(pc,{}).get("投",0), "外資":cd.get(pc,{}).get("外",0)})
            except: pass
            pb.progress((i+1)/len(tt))
        
        st.session_state['rd'], st.session_state['lu'] = rr, dt.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open("c.json",'w') as f: json.dump({'t':st.session_state['lu'],'d':rr}, f)
        except: pass
        st_txt.success(f"✅ 完成！存入 {len(rr)} 檔。")

    if st.session_state['rd']:
        df = pd.DataFrame(st.session_state['rd'])
        with st.expander("⚙️ 參數設定", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            a20 = c1.slider("A策略 MA20 乖離(%)", 1.0, 15.0, 5.0)
            b60 = c2.slider("B策略 MA60 乖離(%)", 1.0, 20.0, 10.0)
            bv = c3.slider("B策略 成交量(張)", 500, 10000, 3000)
            mi = c4.number_input("投信買超大於", -10000, 10000, 100)

        df['A'] = (df['收盤價']>df['MA20']) & (((df['收盤價']-df['MA20'])/df['MA20']*100)<a20)
        df['B'] = (df['成交量']>df['5日均量']) & (df['成交量']>bv) & (((df['收盤價']-df['MA60'])/df['MA60']*100)<b60)
        dff = df[(df['A']|df['B']) & (df['投信']>=mi)].copy()

        if not dff.empty:
            dff['策略'] = dff.apply(lambda x: " + ".join([s for s,c in zip(["🟢 A","🔥 B"],[x['A'],x['B']]) if c]), axis=1)
            dff['乖離(%)'] = round((dff['收盤價']-dff['MA20'])/dff['MA20']*100, 1)
            dff['買區'] = dff['MA20'].apply(lambda x: f"{x:.1f}~{x*1.02:.1f}")
            dff['停損'] = round(dff['MA20']*0.97, 1)
            dp = dff[['代號','名稱','收盤價','策略','投信','外資','乖離(%)','成交量','買區','停損']].sort_values("投信", ascending=False)
            
            m1, m2, m3 = st.columns(3)
            m1.metric("🎯 總數", f"{len(dp)} 檔")
            m2.metric("🔥 投信冠軍", f"{dp.iloc[0]['名稱']}", f"{int(dp.iloc[0]['投信'])} 張")
            m3.metric("📈 最高乖離", f"{dp['乖離(%)'].max()}%")
            
            st.dataframe(dp, use_container_width=True, hide_index=True, column_config={"投信": st.column_config.ProgressColumn("投信", format="%d", min_value=0, max_value=int(dp['投信'].max()) if dp['投信'].max()>0 else 1000)})
            
            sn = st.text_input("快照命名", f"{dt.now().strftime('%Y%m%d_%H%M%S')}_名單")
            if st.button("💾 儲存快照"):
                sd = {}
                try:
                    with open("s.json","r") as f: sd=json.load(f)
                except: pass
                sd[sn] = {"d": dt.now().strftime("%Y-%m-%d %H:%M:%S"), "p": {"A乖離":a20,"B乖離":b60,"B量":bv,"投信":mi}, "r": dp[['代號','名稱','收盤價','策略']].to_dict('records')}
                with open("s.json","w") as f: json.dump(sd, f, ensure_ascii=False)
                st.success("✅ 儲存成功！")
        else: st.warning("⚠️ 無符合股票")
elif page == "競技場":
    st.title("⚔️ 策略競技場")
    if 'ac' not in st.session_state:
        try:
            with open("a.json","r") as f: st.session_state['ac'] = json.load(f)
        except: st.session_state['ac'] = None

    try:
        with open("s.json","r") as f: sd = json.load(f)
    except: sd = {}

    if not sd: st.warning("⚠️ 無快照")
    else:
        ss = st.multiselect("📂 選擇快照", list(sd.keys()), default=list(sd.keys())[-1:])
        if st.button("🚀 結算"):
            if ss:
                cr, ad, pb = [], {}, st.progress(0)
                for idx, sn in enumerate(ss):
                    sr = []
                    for r in sd[sn]["r"]:
                        t, n, ep = r["代號"], r["名稱"], r["收盤價"]
                        try:
                            dfc = yf.download(f"{t}{'.TW' if tw.codes.get(t) and tw.codes[t].market=='上市' else '.TWO'}", period="5d", progress=False)
                            if not dfc.empty:
                                if isinstance(dfc.columns, pd.MultiIndex): dfc.columns = dfc.columns.get_level_values(0)
                                cp = float(dfc['Close'].iloc[-1])
                                sr.append({"代號":t, "名稱":n, "進場":ep, "最新":round(cp,2), "報酬(%)":round((cp-ep)/ep*100,2)})
                        except: pass
                    if sr:
                        dfr = pd.DataFrame(sr)
                        cr.append({"快照":sn, "檔數":len(sr), "平均報酬(%)":round(dfr["報酬(%)"].mean(),2), "勝率(%)":round(len(dfr[dfr["報酬(%)"]>0])/len(dfr)*100,2)})
                        ad[sn] = {"df": dfr.to_dict('records'), "p": sd[sn]["p"]}
                    pb.progress((idx+1)/len(ss))
                
                if cr:
                    cd = {"t": dt.now().strftime("%Y-%m-%d %H:%M:%S"), "cr": cr, "ad": ad}
                    with open("a.json","w") as f: json.dump(cd, f, ensure_ascii=False)
