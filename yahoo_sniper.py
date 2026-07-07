import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime
import streamlit as st

# 安全掛載記憶庫模組
try:
    import broker_memory
except ImportError:
    broker_memory = None

# ==========================================
# 🎯 V31 主力 X 光狙擊槍 (實戰破甲版)
# ==========================================

class YahooSniper:
    def __init__(self):
        # 🛡️ 狙擊手的偽裝衣
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]
        self.session = requests.Session()

    def get_headers(self):
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://tw.stock.yahoo.com/"
        }

    def scan_target(self, stock_code ):
        print(f"🔭 [狙擊鏡開啟] 正在鎖定目標 {stock_code} 的主力動向...")
        
        # 🌟 破甲 1：自動嘗試上市 (.TW) 與上櫃 (.TWO) 網址
        suffixes = [".TW", ".TWO", ""]
        html_content = None
        
        for suffix in suffixes:
            url = f"https://tw.stock.yahoo.com/quote/{stock_code}{suffix}/broker-trading"
            try:
                response = self.session.get(url, headers=self.get_headers( ), timeout=10)
                if response.status_code == 200:
                    html_content = response.text
                    break # 成功抓到網頁，跳出迴圈
            except requests.exceptions.RequestException:
                continue
                
        if not html_content:
            print(f"❌ [狙擊失敗] 目標 {stock_code} 失去聯繫 (404 Not Found 或連線逾時)。")
            return None
            
        # 🌟 破甲 2：降維打擊解析法 (無視 HTML 結構，直接找數學邏輯)
        soup = BeautifulSoup(html_content, "html.parser")
        # 將網頁所有文字抽出，並按行分割
        text = soup.get_text(separator='\n')
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        broker_list = []
        seen_brokers = set() # 防止重複抓取
        
        for i in range(len(lines) - 3):
            broker_name = lines[i]
            
            # 排除純數字與常見的介面干擾文字
            if len(broker_name) >= 2 and not broker_name.isdigit() and broker_name not in ["買進", "賣出", "買賣超", "券商", "張數", "買進張數", "賣出張數"]:
                try:
                    # 嘗試將接下來的三行轉換為數字 (去除千分位逗號)
                    buy = int(lines[i+1].replace(',', ''))
                    sell = int(lines[i+2].replace(',', ''))
                    net = int(lines[i+3].replace(',', ''))
                    
                    # 🎯 終極驗證：買進 - 賣出 必須等於 買賣超！
                    if buy >= 0 and sell >= 0 and (buy - sell == net):
                        if broker_name not in seen_brokers:
                            broker_list.append([broker_name, buy, sell, net])
                            seen_brokers.add(broker_name)
                except ValueError:
                    # 如果轉換數字失敗，代表這不是券商資料，繼續往下找
                    continue

        if broker_list:
            df = pd.DataFrame(broker_list, columns=['券商名稱', '買進張數', '賣出張數', '買賣超張數'])
            # 依照買賣超張數由大到小排序
            df = df.sort_values(by='買賣超張數', ascending=False).reset_index(drop=True)
            print(f"✅ [破解成功] 已突破 Yahoo 防火牆，取得 {len(df)} 筆真實籌碼明細！")
            return df
        else:
            print("⚠️ [解析失敗] 網頁讀取成功，但找不到符合邏輯的券商數據。")
            return None

# ==========================================
# 🖥️ Streamlit UI 介面渲染模組 (對接 app.py Tab 5)
# ==========================================
def render_sniper_module():
    st.header("🎯 主力 X 光狙擊槍 (實戰破甲版)")
    st.caption("無視 Yahoo 防火牆，直接抓取今日真實主力進出明細，並自動存入歷史記憶庫。")
    
    # 讀取從 Tab 2 (雷達室) 傳遞過來的代號 (一鍵潛龍連動)
    default_input = st.session_state.get('sniper_input', '')
    
    target_input = st.text_input(
        "請輸入要狙擊的股票代號 (多檔請用半形逗號分隔，例如: 2376,2382,3231)", 
        value=default_input
    )
    
    if st.button("🔥 一鍵自動狙擊", type="primary"):
        if not target_input:
            st.warning("⚠️ 請先輸入股票代號！")
            return
            
        codes = [c.strip() for c in target_input.split(',') if c.strip()]
        sniper = YahooSniper()
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, code in enumerate(codes):
            status_text.text(f"🔭 正在狙擊目標 {code} ... ({i+1}/{len(codes)})")
            df_result = sniper.scan_target(code)
            
            if df_result is not None and not df_result.empty:
                st.success(f"✅ [{code}] 狙擊成功！取得 {len(df_result)} 筆主力明細。")
                st.dataframe(df_result.head(15), use_container_width=True)
                
                # 💾 自動存入歷史記憶庫
                try:
                    if broker_memory and hasattr(broker_memory, 'save_daily_chips'):
                        broker_memory.save_daily_chips(code, df_result)
                        st.info(f"💾 [{code}] 籌碼已成功存入歷史記憶庫！")
                    else:
                        st.warning("⚠️ 找不到 `broker_memory.save_daily_chips`，無法存檔。")
                except Exception as e:
                    st.error(f"存檔發生錯誤: {e}")
            else:
                st.error(f"❌ [{code}] 狙擊失敗，找不到資料或失去聯繫。")
                
            # 擬人化延遲 (保護 IP 不被 Yahoo 封鎖)
            time.sleep(random.uniform(1.5, 3.0))
            progress_bar.progress(int(((i + 1) / len(codes)) * 100))
            
        status_text.text("🎯 狙擊任務全數完成！")
        
        # 任務完成後，清除 session state 避免下次切換 Tab 時重複觸發
        if 'sniper_input' in st.session_state:
            del st.session_state['sniper_input']

# ==========================================
# ⚙️ 系統整合測試
# ==========================================
if __name__ == "__main__":
    sniper = YahooSniper()
    target_stock = "2376" # 測試技嘉
    df_result = sniper.scan_target(target_stock)
    
    if df_result is not None:
        print(f"\n📊 {target_stock} 今日真實主力進出明細：")
        print(df_result.head(10))
