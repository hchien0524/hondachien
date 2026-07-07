import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os

# 定義本機存檔路徑
DATA_FILE = "hios_data.json"

def save_data_to_local():
    """將 session_state 中的資料存入本機 JSON"""
    data_to_save = {
        "portfolio": st.session_state.get('portfolio', []),
        "watchlist": st.session_state.get('watchlist', [])
    }
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"存檔失敗: {e}")

def render_portfolio_monitor():
    st.header("🛡️ 總司令戰情儀表板 (V31 波段信仰版)")
    st.caption("導入【建倉初衷備忘錄】與【季線波段防守】，過濾短線洗盤噪音，抱緊長線真龍！")
    
    if 'portfolio' not in st.session_state or len(st.session_state['portfolio']) == 0:
        st.info("目前沒有監控中的持股。請從左側邊欄載入戰情包，或在雷達掃描室中加入。")
        return

    total_stocks = len(st.session_state['portfolio'])
    st.markdown(f"**監控總檔數：{total_stocks} 檔**")
    
    cols = st.columns(3)
    
    for idx, item in enumerate(st.session_state['portfolio']):
        code = item.get('code', item.get('Ticker', item.get('代號', '')))
        name = item.get('name', item.get('Name', item.get('名稱', '')))
        cost = float(item.get('cost', item.get('Cost', item.get('成本', item.get('成本價', 0.0)))))
        thesis = item.get('thesis', '')
        
        with cols[idx % 3]:
            card_container = st.container(border=True)
            with card_container:
                display_title = f"### 🎯 [{code}] {name}" if name else f"### 🎯 [{code}]"
                st.markdown(display_title)
                st.markdown(f"**建倉成本: `{cost}`**")
                
                try:
                    tkr = yf.Ticker(f"{code}.TW")
                    hist = tkr.history(period="4mo")
                    if hist.empty:
                        tkr = yf.Ticker(f"{code}.TWO")
                        hist = tkr.history(period="4mo")
                        
                    if not hist.empty and len(hist) >= 20:
                        close = float(hist['Close'].iloc[-1])
                        ma20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
                        
                        if len(hist) >= 60:
                            ma60 = float(hist['Close'].rolling(window=60).mean().iloc[-1])
                        else:
                            ma60 = ma20 
                        
                        ret_pct = ((close - cost) / cost) * 100 if cost > 0 else 0
                        bias_20 = ((close - ma20) / ma20) * 100
                        dist_60ma = ((close - ma60) / ma60) * 100
                        
                        # ==========================================
                        # ⚖️ V31 波段信仰防守邏輯 (捨棄短線月線停損)
                        # ==========================================
                        if close < ma60:
                            status = "☠️ 跌破季線 (波段防守線，建議重新評估)"
                            st.error(status)
                        elif bias_20 >= 15.0:
                            status = "🚨 乖離過熱 (動能極強，可考慮逢高停利一半)"
                            st.warning(status)
                        else:
                            status = "🟢 季線之上 (波段續抱，無視短線洗盤)"
                            st.success(status)
                        
                        # 顯示核心數據
                        st.metric("最新收盤", f"{close:.2f}", f"{ret_pct:.2f}%")
                        st.caption(f"月線: {ma20:.2f} | 季線(生命線): {ma60:.2f}")
                        
                        # 🛡️ 季線防守血條
                        hp_val = max(0.0, min(100.0, 50 + dist_60ma * 2)) 
                        hp_color = "#00cc66" if dist_60ma > 0 else "#ff3333"
                        st.markdown(
                            f"""
                            <div style="width: 100%; background-color: #444444; border-radius: 5px; margin-bottom: 10px;">
                              <div style="width: {hp_val}%; height: 8px; background-color: {hp_color}; border-radius: 5px;"></div>
                            </div>
                            """, unsafe_allow_html=True
                        )
                    else:
                        st.write("⚪ 無足夠報價資料")
                except Exception as e:
                    st.write("⚪ 連線失敗")
                
                # 📝 建倉初衷備忘錄
                new_thesis = st.text_area(
                    "📝 建倉初衷與防守策略", 
                    value=thesis, 
                    height=100, 
                    key=f"thesis_{idx}",
                    help="把 Copilot 的分析或您的長線理由寫在這裡。下次大跌時先看這段話再決定是否停損！"
                )
                
                if new_thesis != thesis:
                    st.session_state['portfolio'][idx]['thesis'] = new_thesis
                    save_data_to_local()
                    
                if st.button("🗑️ 撤退/刪除", key=f"del_{idx}", use_container_width=True):
                    st.session_state['portfolio'].pop(idx)
                    save_data_to_local()
                    st.rerun()
