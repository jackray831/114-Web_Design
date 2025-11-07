# main.py
import uvicorn
import json  # 導入 json 模組
from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect, Query
from fastapi.templating import Jinja2Templates
from typing import Dict, List # 導入 List

# ... (FastAPI 和 Jinja2 實例化) ...
app = FastAPI()
templates = Jinja2Templates(directory="templates")


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
        self.active_connections[websocket] = nickname

    def disconnect(self, websocket: WebSocket) -> str:
        """斷開一個 WebSocket 連線"""
        nickname = self.active_connections.pop(websocket, "某人")
        return nickname

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


# --- HTTP 路由 (用來提供前端頁面) ---
@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# --- WebSocket 路由 (聊天室核心) ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, nickname: str = Query("訪客")):
    
    # 接受新連線
    await manager.connect(websocket, nickname)
    
    # 1. 廣播「加入」的系統訊息
    join_message = {"type": "system", "message": f"{nickname} 加入了聊天室"}
    await manager.broadcast(join_message)
    
    # 2. 廣播「更新成員列表」指令
    member_list = manager.get_member_list()
    update_list_message = {"type": "member_list_update", "members": member_list}
    await manager.broadcast(update_list_message)
    
    try:
        # 保持迴圈，監聽來自客戶端的訊息
        while True:
            data = await websocket.receive_text()
            
            # 廣播「聊天」訊息
            chat_message = {"type": "chat", "nickname": nickname, "message": data}
            await manager.broadcast(chat_message)
            
    except WebSocketDisconnect:
        # 處理斷線
        nickname_left = manager.disconnect(websocket)
        
        # 1. 廣播「離開」的系統訊息
        leave_message = {"type": "system", "message": f"{nickname_left} 離開了聊天室"}
        await manager.broadcast(leave_message)
        
        # 2. 廣播「更新成員列表」指令
        member_list = manager.get_member_list()
        update_list_message = {"type": "member_list_update", "members": member_list}
        await manager.broadcast(update_list_message)

# 允許在 Python 腳本中直接執行
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)