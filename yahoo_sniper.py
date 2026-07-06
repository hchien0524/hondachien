import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime
import broker_memory

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
# ⚙️ 系統整合測試
# ==========================================
if __name__ == "__main__":
    sniper = YahooSniper()
    target_stock = "2376" # 測試技嘉
    df_result = sniper.scan_target(target_stock)
    
    if df_result is not None:
        print(f"\n📊 {target_stock} 今日真實主力進出明細：")
        print(df_result.head(10))
