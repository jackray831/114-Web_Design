# main.py
import uvicorn
import json
import sqlite3
import os
import re
import uuid # 用來產生唯一檔名
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, status, Header, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles # 用來提供靜態檔案存取
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from dotenv import load_dotenv

DB_NAME = "Database.db"

# --- JWT 設定 ---
load_dotenv()
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- 定義檔案上傳目錄 ---
UPLOAD_DIR = "static/uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# [新增] 密碼雜湊器 (用來把密碼加密，不要存明碼！)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def init_db():
    """初始化資料庫"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # [修改] 增加 msg_type 欄位，用來區分是 'text' 還是 'image'
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nickname TEXT,
                  message TEXT,
                  msg_type TEXT,
                  timestamp TEXT)''')
    
    # [新增] 建立使用者表 (username 是主鍵，不可重複)
    # 注意：password_hash 存的是加密後的字串，不是明碼
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY,
                  password_hash TEXT)''')

    conn.commit()
    conn.close()

# --- 認證相關函式 ---
# [新增] 驗證密碼是否正確
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# [新增] 將密碼加密
def get_password_hash(password):
    return pwd_context.hash(password)

# [新增] 產生 JWT Token
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    # payload 裡面放入過期時間 (exp)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# [新增] 從 Token 解析出使用者 (用於 WebSocket 驗證)
def get_current_user_from_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None

# [新增] 定義註冊/登入的資料格式
class UserAuth(BaseModel):
    username: str
    password: str

# [新增] 專門給註冊用的模型，多一個確認密碼欄位
class UserRegister(BaseModel):
    username: str
    password: str
    confirm_password: str

# [新增] 更改密碼用的資料模型
class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
    confirm_new_password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str

def save_message(nickname, message, timestamp, msg_type="text"):
    """儲存訊息 (支援文字與圖片)"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # [修改] 插入時多存一個 msg_type
    c.execute("INSERT INTO messages (nickname, message, msg_type, timestamp) VALUES (?, ?, ?, ?)",
              (nickname, message, msg_type, timestamp))
    conn.commit()
    conn.close()

def get_recent_messages(limit=50):
    """取得最近的歷史訊息"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # [修改] 讀取時也要抓 msg_type
    c.execute("SELECT nickname, message, msg_type, timestamp FROM messages ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    
    # 將資料轉為字典格式
    history = []
    for row in rows:
        msg_data = {
            "nickname": row[0],
            "time": row[3],
            "type": row[2]  # 從資料庫讀取型別 (text 或 image)
        }
        
        if row[2] == "image":
            msg_data["imageData"] = row[1] # 如果是圖片，內容放在 imageData
        elif row[2] == "file":
            msg_data["imageData"] = row[1]
            msg_data["filename"] = "附件"
        elif row[2] == "video":
            msg_data["imageData"] = row[1]
            msg_data["filename"] = "影片"
        else:
            msg_data["message"] = row[1]   # 如果是文字，內容放在 message
            
        history.append(msg_data)

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

# 掛載靜態檔案路徑 (這行一定要加，讓前端讀得到圖片)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- CORS 設定 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在開發階段，允許所有來源連線 (生產環境建議指定特定網域)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [修改] 註冊 API：改用 UserRegister 模型並加入驗證邏輯
@app.post("/register")
async def register(user: UserRegister):
    # 1. 檢查兩次密碼是否輸入一致
    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="兩次輸入的密碼不一致")

    # 2. 檢查密碼複雜度 (例如：至少8碼，且包含英文與數字)
    # ^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$ 是一個常見的正則表達式
    if len(user.password) < 8:
        raise HTTPException(status_code=400, detail="密碼長度至少需要 8 個字元")

    if not re.search(r"[A-Za-z]", user.password) or not re.search(r"\d", user.password):
        raise HTTPException(status_code=400, detail="密碼必須包含至少一個英文字母與一個數字")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 3. 檢查帳號是否已存在
    c.execute("SELECT username FROM users WHERE username = ?", (user.username,))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="此帳號已被註冊")
    
    # 4. 將密碼加密後存入資料庫
    hashed_password = get_password_hash(user.password)
    c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", 
              (user.username, hashed_password))
    
    conn.commit()
    conn.close()
    return {"message": "User created successfully"}

# [新增] 登入 API
@app.post("/token", response_model=Token)
async def login_for_access_token(user_data: UserAuth):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 找使用者
    c.execute("SELECT username, password_hash FROM users WHERE username = ?", (user_data.username,))
    row = c.fetchone()
    conn.close()
    
    # 驗證帳號存在 且 密碼正確
    if not row or not verify_password(user_data.password, row[1]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 登入成功，發放 Token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_data.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "username": user_data.username
    }

# [新增] 更改密碼 API
@app.post("/change-password")
async def change_password(
    req: ChangePasswordRequest, 
    authorization: str = Header(None) # 從 Header 取得 Token
):
    # 1. 驗證 Token 是否存在
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登入或 Token 無效")
    
    token = authorization.split(" ")[1]
    username = get_current_user_from_token(token)
    
    if not username:
        raise HTTPException(status_code=401, detail="Token 無效或過期")

    # 2. 驗證新密碼格式 (與註冊時相同的邏輯)
    if req.new_password != req.confirm_new_password:
        raise HTTPException(status_code=400, detail="兩次新密碼輸入不一致")

    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="新密碼長度至少需要 8 個字元")
    
    if not re.search(r"[A-Za-z]", req.new_password) or not re.search(r"\d", req.new_password):
        raise HTTPException(status_code=400, detail="新密碼必須包含至少一個英文字母與一個數字")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 3. 取得目前使用者資料
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="使用者不存在")
    
    current_password_hash = row[0]

    # 4. 驗證舊密碼是否正確
    if not verify_password(req.old_password, current_password_hash):
        conn.close()
        raise HTTPException(status_code=400, detail="舊密碼錯誤")

    # 5. 更新密碼
    new_hashed_password = get_password_hash(req.new_password)
    c.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_hashed_password, username))
    conn.commit()
    conn.close()

    return {"message": "密碼修改成功"}

# [新增] 專門處理圖片上傳的 API
# 前端會用 Form Data (multipart/form-data) 傳送檔案到這裡
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # 允許的副檔名類型
        allowed_extensions = ["jpg", "jpeg", "png", "gif", "pdf", "doc", "docx", "zip", "rar","mp4", "webm"]

        # 取得副檔名
        filename_ext = file.filename.split(".")[-1].lower()
        if filename_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail="不支援的檔案類型")

        # 產生亂碼檔名
        unique_filename = f"{uuid.uuid4()}.{filename_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        # 儲存檔案
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        return {"url": f"/static/uploads/{unique_filename}"}

    except Exception as e:
        print(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="檔案上傳失敗")

# --- WebSocket 路由 (聊天室核心) ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    # 注意：這裡將 nickname 改為接收 token

    if token is None:
        await websocket.close(code=4003, reason="Token missing")
        return
    
    # 1. 驗證 Token，取得使用者名稱
    username = get_current_user_from_token(token)
    
    if username is None:
        # Token 無效或過期
        await websocket.close(code=4003, reason="Invalid token")
        return

    # 2. 嘗試連線
    success = await manager.connect(websocket, username)
    if not success:
        return # 這裡可能是重複登入

    # 連線成功後，傳送歷史訊息
    history = get_recent_messages()
    # 我們定義一個新的類型 'history'
    await websocket.send_text(json.dumps({"type": "history", "messages": history}))
    
    # 廣播加入訊息
    await manager.broadcast({"type": "system", "message": f"{username} 加入了聊天室"})
    await manager.broadcast({"type": "member_list_update", "members": manager.get_member_list()})
    
    try:
        while True:
            data = await websocket.receive_text()

            try:
                parsed = json.loads(data)

                # [修改] 加入型別檢查：如果解析出來不是字典 (例如是 int, list, string)，則視為格式不符
                if not isinstance(parsed, dict):
                    raise ValueError("Parsed JSON is not a dictionary")

                msg_type = parsed.get("type")
                timestamp = datetime.now().strftime("%H:%M")

                if msg_type == "image":
                    # [修改重點在此]
                    # 現在前端傳過來的 imageData 不再是巨大的 Base64，
                    # 而是剛剛從 /upload API 拿到的 "網址" (例如 /static/uploads/xxx.jpg)
                    image_url = parsed.get("imageData")

                    if image_url:
                        # 1. 存入資料庫 (只存網址)
                        save_message(username, image_url, timestamp, msg_type="image")
                        
                        # 2. 廣播給所有人 (包含傳送者)
                        await manager.broadcast({
                            "type": "image",
                            "nickname": username,
                            "imageData": image_url, # 這裡廣播網址
                            "time": timestamp
                        })
                elif msg_type == "file":
                    file_url = parsed.get("imageData")  # 雖然是檔案，但欄位仍用 imageData
                    filename = parsed.get("filename", "附件")

                    if file_url:
                        save_message(username, file_url, timestamp, msg_type="file")
                        await manager.broadcast({
                            "type": "file",
                            "nickname": username,
                            "imageData": file_url,
                            "filename": filename,
                            "time": timestamp
                        })
                elif msg_type == "video":
                    video_url = parsed.get("imageData")
                    filename = parsed.get("filename", "影片")

                    if video_url:
                        save_message(username, video_url, timestamp, msg_type="video")
                        await manager.broadcast({
                            "type": "video",
                            "nickname": username,
                            "imageData": video_url,
                            "filename": filename,
                            "time": timestamp
                        })

                else:
                    # 一般文字訊息
                    save_message(username, data, timestamp, msg_type="text")
                    await manager.broadcast({
                        "type": "chat",
                        "nickname": username,
                        "message": data,
                        "time": timestamp
                    })

            # [修改] 除了 JSONDecodeError，也要捕捉 ValueError (我們剛剛手動引發的) 或 AttributeError
            except (json.JSONDecodeError, ValueError, AttributeError) as e:
                # 錯誤處理
                timestamp = datetime.now().strftime("%H:%M")
                # 這裡將 data (原始字串) 當作純文字訊息儲存
                save_message(username, data, timestamp, msg_type="text")
                await manager.broadcast({
                    "type": "chat",
                    "nickname": username,
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