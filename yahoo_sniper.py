import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime
import broker_memory

# ==========================================
# 🎯 V31 主力 X 光狙擊槍 (實戰爬蟲版)
# ==========================================

class YahooSniper:
    def __init__(self):
        # 🛡️ 狙擊手的偽裝衣 (隨機切換瀏覽器標頭，防止被 Yahoo 封鎖 IP)
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
        ]

    def get_headers(self):
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://tw.stock.yahoo.com/"
        }

    def scan_target(self, stock_code ):
        """
        執行狙擊任務：潛入 Yahoo 股市抓取「單日券商進出明細」
        """
        print(f"🔭 [狙擊鏡開啟] 正在鎖定目標 {stock_code} 的主力動向...")
        
        # Yahoo 股市券商進出的標準 URL
        url = f"https://tw.stock.yahoo.com/quote/{stock_code}/broker-trading"
        
        try:
            # 1. 潛入目標網站
            response = requests.get(url, headers=self.get_headers( ), timeout=10)
            response.raise_for_status() 
            
            # 2. 解析網頁原始碼
            soup = BeautifulSoup(response.text, "html.parser")
            broker_list = []
            
            # 🌟 實戰解析邏輯：尋找 Yahoo 的資料列表 (li 或 div row)
            # Yahoo 的 DOM 結構常變，我們用最穩定的特徵抓取：尋找包含數字的區塊
            rows = soup.find_all("li", class_="List(n)")
            
            for row in rows:
                cols = row.find_all("div")
                # 確保這是一行有效的數據 (至少要有 券商名, 買, 賣, 買賣超)
                if len(cols) >= 4:
                    try:
                        # 提取文字並清理空白
                        texts = [c.text.strip() for c in cols if c.text.strip()]
                        
                        # 確保抓到的是券商名稱 (不是純數字的序號)
                        if len(texts) >= 4 and not texts[0].isdigit():
                            broker_name = texts[0]
                            # 將字串轉為整數 (去除千分位逗號)
                            buy_vol = int(texts[1].replace(',', ''))
                            sell_vol = int(texts[2].replace(',', ''))
                            net_vol = int(texts[3].replace(',', ''))
                            
                            broker_list.append([broker_name, buy_vol, sell_vol, net_vol])
                    except ValueError:
                        # 如果轉換數字失敗，代表這行可能是標題或廣告，直接跳過
                        continue 

            # 3. 轉換為 Pandas 裝甲車
            if broker_list:
                df = pd.DataFrame(broker_list, columns=['券商名稱', '買進張數', '賣出張數', '買賣超張數'])
                # 依照買賣超張數由大到小排序
                df = df.sort_values(by='買賣超張數', ascending=False).reset_index(drop=True)
                print("✅ [破解成功] 已突破 Yahoo 防火牆，取得真實籌碼明細！")
                return df
            else:
                print("⚠️ [解析失敗] 網頁讀取成功，但找不到券商表格。Yahoo 可能更改了網頁結構。")
                return None
            
        except requests.exceptions.RequestException as e:
            print(f"❌ [狙擊失敗] 目標 {stock_code} 失去聯繫或防護過強：{e}")
            return None

# ==========================================
# ⚙️ 系統整合測試 (Sniper + Memory)
# ==========================================
if __name__ == "__main__":
    sniper = YahooSniper()
    target_stock = "2376" # 拿今天的榜眼「技嘉」來測試
    
    df_result = sniper.scan_target(target_stock)
    
    if df_result is not None:
        print(f"\n📊 {target_stock} 今日真實主力進出明細：")
        print(df_result.head(10)) # 印出前 10 大主力
