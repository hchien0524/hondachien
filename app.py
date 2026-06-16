import json,os,requests,time
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

if page=="雷達":
    st.title("🚀 HIOS 波段雷達 (V16.2 全市場雙引擎)")
    if 'rd' not in st.session_state:
        try:
            with open("c.json",'r') as f:
                d=json.load(f)
                st.session_state['rd'],st.session_state['lu']=d['d'],d['t']
        except: st.session_state['rd'],st.session_state['lu']=[], "無"

    @st.cache_data
    def get_t(m):
        tm="上市" if "上市" in m else "上櫃"
        return [f"{c}{'.TW' if tm=='上市' else '.TWO'}" for c,i in tw.codes.items() if i.type=='股票' and i.market==tm and len(c)==4], {c:i.name for c,i in tw.codes.items() if i.type=='股票' and i.market==tm and len(c)==4}

    st.sidebar.info(f"💾 更新: {st.session_state['lu']}")
    sm = st.sidebar.radio("範圍", ("自選","上市","上櫃","全市場"))
    ti = st.sidebar.text_area("自選代號","2382,3413") if sm=="自選" else ""
    cs = st.sidebar.radio("籌碼", ("CSV","API"))
    uc = st.sidebar.file_uploader("CSV",type=["csv"]) if cs=="CSV" else None

    if st.sidebar.button("🚀 抓取"):
        cd={}
        if uc:
            df=pd.read_csv(uc)
            cc,fc,ic=df.columns[0],df.columns[df.columns.str.contains('外資')][0],df.columns[df.columns.str.contains('投信')][0]
            for _,r in df.iterrows(): cd[str(r[cc]).replace('=','').replace('"','').strip()]={"外":pd.to_numeric(str(r[fc]).replace(',',''),errors='coerce')or 0,"投":pd.to_numeric(str(r[ic]).replace(',',''),errors='coerce')or 0}
        elif cs=="API":
            try:
                for i in requests.get("https://openapi.twse.com.tw/v1/fund/T86_ALL",timeout=5 ).json(): cd[str(i.get('Code','')).strip()]={"外":float(str(i.get('ForeignInvestorDifference','0')).replace(',',''))/1000,"投":float(str(i.get('InvestmentTrustDifference','0')).replace(',',''))/1000}
                for i in requests.get("https://www.tpex.org.tw/openapi/v1/t112sb0eb",timeout=5 ).json():
                    c=str(i.get('SecuritiesCompanyCode','')).strip()
                    if c not in cd: cd[c]={"外":0,"投":0}
                    cd[c]["外"]=float(str(i.get('Difference','0')).replace(',',''))/1000
                for i in requests.get("https://www.tpex.org.tw/openapi/v1/t112sb0ec",timeout=5 ).json():
                    c=str(i.get('SecuritiesCompanyCode','')).strip()
                    if c not in cd:
