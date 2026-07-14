import streamlit as st
import pandas as pd
import sqlite3
import requests
import datetime
import time

# ==========================================
# 💾 系統設定與資料庫初始化
# ==========================================
DB_FILE = "broker_memory.db"

def init_sector_db():
    """初始化族群資金歷史資料表"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sector_flow_history (
                record_date TEXT,
                sector_name TEXT,
                trade_value REAL,
                percentage REAL,
                PRIMARY KEY (record_date, sector_name)
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"資料庫初始化失敗: {e}")

# ==========================================
# 📥 官方數據直連採集引擎 (TWSE) - 終極偽裝版
# ==========================================
def fetch_twse_sector_data():
    """直連台灣證交所抓取各類股成交金額 (BFIAMU)"""
    session = requests.Session()
    
    # 🛡️ 破解防線 1：完全偽裝成真實的 Chrome 瀏覽器
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.twse.com.tw/zh/trading/historical/bfiamu.html',
        'X-Requested-With': 'XMLHttpRequest',
        'Connection': 'keep-alive'
    }
    session.headers.update(headers )
    
    try:
        # 🛡️ 破解防線 2：先拜訪網頁取得官方 Cookie (俗稱：敲門)
        try:
            session.get("https://www.twse.com.tw/zh/trading/historical/bfiamu.html", timeout=5 )
            time.sleep(0.5) # 假裝人類停頓半秒
        except:
            pass 
            
        # 🛡️ 破解防線 3：加上動態時間戳記 (Timestamp) 騙過快取與機器人驗證
        ts = int(time.time() * 1000)
        url_primary = f"https://www.twse.com.tw/exchangeReport/BFIAMU?response=json&_={ts}"
        url_backup = f"https://www.twse.com.tw/rwd/zh/afterTrading/BFIAMU?response=json&_={ts}"
        
        # 嘗試連線主節點
        response = session.get(url_primary, timeout=10 )
        try:
            data = response.json()
        except Exception:
            # 若主節點失敗，休眠 1 秒後切換備援節點
            time.sleep(1)
            response = session.get(url_backup, timeout=10)
            try:
                data = response.json()
            except Exception:
                # 🛡️ 終極診斷：如果還是失敗，把證交所回傳的真實內容印出來，讓我們知道死在哪裡
                error_preview = response.text[:100].replace('\n', ' ')
                return None, f"證交所防火牆阻擋了連線 (HTTP {response.status_code})。回傳內容: {error_preview}..."
            
        if data.get('stat') != 'OK':
            return None, "證交所 API 回應異常或今日無數據"
            
        # 解析官方數據 (BFIAMU 欄位: 0.分類指數名稱, 1.成交股數, 2.成交金額, 3.成交筆數, 4.漲跌指數)
        raw_data = data.get('data', [])
        parsed_data = []
        total_market_value = 0.0
        
        for row in raw_data:
            sector_name = row[0].strip()
            # 排除非單一產業的統計大項
            if sector_name in ['總計', '合計', '電子工業', '未含金融電子股', '未含金融股', '電子類指數', '金融保險類指數', '未含電子股']:
                continue
                
            # 清洗成交金額 (Index 2 是成交金額，去除逗號轉數字)
            trade_value_str = str(row[2]).replace(',', '')
            try:
                trade_value = float(trade_value_str)
            except:
                trade_value = 0.0
                
            parsed_data.append({
                'sector_name': sector_name,
                'trade_value': trade_value
            })
            total_market_value += trade_value
            
        # 計算資金佔比
        for item in parsed_data:
            if total_market_value > 0:
                item['percentage'] = round((item['trade_value'] / total_market_value) * 100, 2)
            else:
                item['percentage'] = 0.0
                
        df = pd.DataFrame(parsed_data)
        
        # 取得官方報表日期
        tw_date = data.get('date', '')
        if tw_date and len(tw_date) == 8:
            year = int(tw_date[:4])
            month = int(tw_date[4:6])
            day = int(tw_date[6:])
            record_date = f"{year}-{month:02d}-{day:02d}"
        else:
            record_date = datetime.datetime.now().strftime("%Y-%m-%d")
            
        return df, record_date
        
    except Exception as e:
        return None, f"連線失敗: {e}"

# ==========================================
# 💾 記憶歸檔與戰報分析引擎
# ==========================================
def save_to_db(df, record_date):
    """將今日數據寫入 SQLite 永久記憶庫"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        insert_sql = '''
            INSERT INTO sector_flow_history (record_date, sector_name, trade_value, percentage)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(record_date, sector_name) 
            DO UPDATE SET trade_value=excluded.trade_value, percentage=excluded.percentage
        '''
        
        records = []
        for _, row in df.iterrows():
            records.append((record_date, row['sector_name'], row['trade_value'], row['percentage']))
            
        cursor.executemany(insert_sql, records)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"寫入資料庫失敗: {e}")
        return False

def analyze_invisible_champions():
    """跨日比對：抓出連續 3 天資金流入的隱形冠軍"""
    try:
        conn = sqlite3.connect(DB_FILE)
        # 抓取最近的 3 個交易日
        dates_query = "SELECT DISTINCT record_date FROM sector_flow_history ORDER BY record_date DESC LIMIT 3"
        dates_df = pd.read_sql_query(dates_query, conn)
        
        if len(dates_df) < 3:
            conn.close()
            return None, f"⚠️ 歷史數據不足！目前僅有 {len(dates_df)} 天數據，需累積 3 天才能啟動隱形冠軍濾網。"
            
        recent_dates = dates_df['record_date'].tolist()
        recent_dates.sort() # 排序為 [Day1, Day2, Day3(最新)]
        d1, d2, d3 = recent_dates[0], recent_dates[1], recent_dates[2]
        
        # 抓取這 3 天的所有數據
        data_query = f"SELECT * FROM sector_flow_history WHERE record_date IN ('{d1}', '{d2}', '{d3}')"
        df_all = pd.read_sql_query(data_query, conn)
        conn.close()
        
        # 樞紐分析：將日期轉為欄位，方便比對
        df_pivot = df_all.pivot(index='sector_name', columns='record_date', values='percentage').reset_index()
        df_pivot = df_pivot.dropna() # 排除資料不全的族群
        
        # ⚔️ 核心濾網：連續 3 天資金佔比上升 (Day1 < Day2 < Day3)
        champions = df_pivot[
            (df_pivot[d1] < df_pivot[d2]) & 
            (df_pivot[d2] < df_pivot[d3])
        ].copy()
        
        # 計算 3 天總增幅
        if not champions.empty:
            champions['3日增幅(%)'] = round(champions[d3] - champions[d1], 2)
            champions = champions.sort_values(by='3日增幅(%)', ascending=False).reset_index(drop=True)
            
        return champions, recent_dates
        
    except Exception as e:
        return None, f"分析失敗: {e}"

# ==========================================
# 🖥️ UI 戰情面板渲染
# ==========================================
def render_sector_flow_ui():
    init_sector_db()
    
    st.header("🌊 V36 族群資金活水 (Top-Down 宏觀雷達)")
    st.markdown("透過直連證交所官方數據，追蹤各類股資金流向，精準抓出**「連續 3 天資金偷偷流入」**的隱形冠軍板塊！")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("🔄 1. 獲取今日最新族群資金 (每日 14:00 後執行)", type="primary", use_container_width=True):
            with st.spinner("正在直連台灣證交所抓取官方數據 (已啟動防封鎖偽裝)..."):
                df_today, result = fetch_twse_sector_data()
                
                if df_today is not None:
                    if save_to_db(df_today, result):
                        st.success(f"✅ 成功抓取並歸檔 {result} 的官方資金數據！")
                else:
                    st.error(result)
                    
    with col2:
        st.markdown("🔗 **🕵️‍♂️ 官方查帳直達車：** [點我前往 TWSE 證交所官方網頁核對數據](https://www.twse.com.tw/zh/trading/historical/bfiamu.html )")
        st.caption("💡 系統數據 100% 來自官方，拒絕黑箱，歡迎總司令隨時查帳！")

    st.divider()
    
    # 產出戰報
    st.subheader("👑 隱形冠軍戰報 (連續 3 天資金流入)")
    champions, dates_info = analyze_invisible_champions()
    
    if isinstance(dates_info, str): # 代表回傳的是錯誤/警告訊息
        st.warning(dates_info)
    elif champions is not None and not champions.empty:
        d1, d2, d3 = dates_info[0], dates_info[1], dates_info[2]
        st.success(f"🎯 發現資金正在偷偷建倉！比對區間：{d1} ➔ {d3}")
        
        # 格式化顯示
        display_df = champions[['sector_name', d1, d2, d3, '3日增幅(%)']].copy()
        display_df.columns = ['族群名稱', f'{d1} 佔比(%)', f'{d2} 佔比(%)', f'最新 {d3} 佔比(%)', '3日總增幅(%)']
        st.dataframe(display_df, use_container_width=True)
        
        st.info("💡 **CIO 戰略提示：** 請將 V35 雷達掃出的個股，與上方的「隱形冠軍族群」進行交叉比對。若兩者重疊，即為勝率極高的【族群共振真龍】！")
    else:
        st.info("📉 目前無任何族群符合「連續 3 天資金流入」的嚴格標準。資金可能處於快速輪動或觀望狀態。")

    # 原始數據展開區
    with st.expander("📊 展開查看今日所有族群原始資金佔比 (供查帳驗算)"):
        try:
            conn = sqlite3.connect(DB_FILE)
            latest_date_query = "SELECT MAX(record_date) FROM sector_flow_history"
            latest_date = pd.read_sql_query(latest_date_query, conn).iloc[0,0]
            
            if latest_date:
                raw_query = f"SELECT sector_name AS '族群名稱', trade_value AS '成交金額(元)', percentage AS '資金佔比(%)' FROM sector_flow_history WHERE record_date = '{latest_date}' ORDER BY percentage DESC"
                df_raw = pd.read_sql_query(raw_query, conn)
                st.write(f"📅 數據日期：{latest_date}")
                st.dataframe(df_raw, use_container_width=True)
            else:
                st.write("尚無歷史數據。")
            conn.close()
        except Exception as e:
            st.write("無法讀取原始數據。")
