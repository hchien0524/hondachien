import requests
import json
import streamlit as st

class GistManager:
    """HIOS Wave Radar 專屬雲端記憶體 (取代 Base64)"""
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        # 從 session_state 讀取目前的 gist_id (若有)
        self.gist_id = st.session_state.get('gist_id', "")

    def save_data(self, filename: str, data: list) -> bool:
        """將陣地資料同步至雲端"""
        payload = {
            "description": "HIOS Wave Radar Cloud Memory",
            "public": False,
            "files": {
                filename: {
                    "content": json.dumps(data, ensure_ascii=False, indent=2)
                }
            }
        }
        try:
            if self.gist_id:
                # 更新現有記憶
                url = f"https://api.github.com/gists/{self.gist_id}"
                res = requests.patch(url, headers=self.headers, json=payload )
            else:
                # 創建新記憶
                url = "https://api.github.com/gists"
                res = requests.post(url, headers=self.headers, json=payload )
                if res.status_code == 201:
                    self.gist_id = res.json()['id']
                    st.session_state['gist_id'] = self.gist_id
            return res.status_code in [200, 201]
        except Exception as e:
            st.error(f"雲端同步失敗: {e}")
            return False

    def load_data(self, gist_id: str, filename: str) -> list:
        """從雲端喚醒陣地資料"""
        try:
            url = f"https://api.github.com/gists/{gist_id}"
            res = requests.get(url, headers=self.headers )
            if res.status_code == 200:
                files = res.json().get('files', {})
                if filename in files:
                    content = files[filename]['content']
                    self.gist_id = gist_id
                    st.session_state['gist_id'] = gist_id
                    return json.loads(content)
            return None
        except Exception as e:
            st.error(f"雲端讀取失敗: {e}")
            return None
