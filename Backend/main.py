# main.py
import uvicorn
import json  # 導入 json 模組
import sqlite3
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Dict, List # 導入 List

DB_NAME = "chat_log.db"

def init_db():
    """初始化資料庫"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # 建立 messages 表格，包含時間戳記
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nickname TEXT,
                  message TEXT,
                  timestamp TEXT)''')
    conn.commit()
    conn.close()

def save_message(nickname, message, timestamp):
    """儲存訊息"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO messages (nickname, message, timestamp) VALUES (?, ?, ?)",
              (nickname, message, timestamp))
    conn.commit()
    conn.close()

def get_recent_messages(limit=50):
    """取得最近的歷史訊息"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # 倒序抓取最新的 50 筆
    c.execute("SELECT nickname, message, timestamp FROM messages ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    
    # 將資料轉為字典格式，並反轉順序 (讓舊訊息在上面)
    history = [
        {"type": "chat", "nickname": row[0], "message": row[1], "time": row[2]} 
        for row in rows
    ]
    return history[::-1]

# 伺服器啟動時，初始化資料庫
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

class ConnectionManager:
    """管理 WebSocket 連線的類別"""
    def __init__(self):
        # 儲存活躍連線 (WebSocket: 暱稱)
        self.active_connections: Dict[WebSocket, str] = {}

    def get_member_list(self) -> List[str]:
        """取得所有成員的暱稱列表"""
        return list(self.active_connections.values())

    async def connect(self, websocket: WebSocket, nickname: str):
        """接受一個新的 WebSocket 連線"""
        await websocket.accept()
        # --- 檢查暱稱是否重複 ---
        if nickname in self.active_connections.values():
            # 代碼 4003 代表 "Forbidden" 或自定義錯誤
            await websocket.close(code=4003, reason="Nickname taken")
            return False  # 連線失敗
            
        self.active_connections[websocket] = nickname
        return True   # 連線成功

    def disconnect(self, websocket: WebSocket) -> str:
        """斷開一個 WebSocket 連線"""
        return self.active_connections.pop(websocket, "某人")

    async def broadcast(self, payload: dict):
        """
        廣播 JSON 訊息給所有已連線的 WebSocket
        payload 是一個字典，我們會將它轉換為 JSON 字串
        """
        message_str = json.dumps(payload)  # 將字典轉為 JSON 字串
        for connection in self.active_connections:
            await connection.send_text(message_str)

# 實例化連線管理器
manager = ConnectionManager()

# ... (FastAPI 實例化) ...
app = FastAPI(lifespan=lifespan)

# --- CORS 設定 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在開發階段，允許所有來源連線 (生產環境建議指定特定網域)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- WebSocket 路由 (聊天室核心) ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, nickname: str = Query("訪客")):
    
    # 嘗試連線
    success = await manager.connect(websocket, nickname)
    if not success:
        return  # 如果暱稱重複，直接結束函式

    # --- 連線成功後，立刻傳送歷史訊息給該使用者 ---
    history = get_recent_messages()
    # 我們定義一個新的類型 'history'
    await websocket.send_text(json.dumps({"type": "history", "messages": history}))
    
    # 廣播加入訊息
    await manager.broadcast({"type": "system", "message": f"{nickname} 加入了聊天室"})
    await manager.broadcast({"type": "member_list_update", "members": manager.get_member_list()})
    
    try:
        while True:
            data = await websocket.receive_text()

            # --- 產生時間戳記 ---
            timestamp = datetime.now().strftime("%H:%M")
            
            # --- 存入資料庫 ---
            save_message(nickname, data, timestamp)
            
            # 廣播訊息 (包含時間)
            await manager.broadcast({
                "type": "chat", 
                "nickname": nickname, 
                "message": data,
                "time": timestamp 
            })
            
    except WebSocketDisconnect:
        nickname_left = manager.disconnect(websocket)
        # 廣播離開訊息
        await manager.broadcast({"type": "system", "message": f"{nickname_left} 離開了聊天室"})
        await manager.broadcast({"type": "member_list_update", "members": manager.get_member_list()})

# 允許在 Python 腳本中直接執行
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)