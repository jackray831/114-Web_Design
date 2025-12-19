<template>
  <div class="container">
    
    <div class="chat-ui" :class="{ 'blurred': !isJoined }">
      <div class="header">
        <h1>聊天室</h1>
        <div class="header-right">
          <span class="user-badge">我是: {{ isJoined ? currentUser : '未登入' }}</span>
          <button v-if="isJoined" @click="logout" class="logout-btn">登出</button>
        </div>
      </div>

      <div class="main-area">
        <div class="chat-area">
          <ul ref="messagesContainer" class="messages-list">
            <li 
              v-for="(msg, index) in messages" 
              :key="index"
              :class="{ 'system-msg': msg.type === 'system', 'my-msg': msg.nickname === currentUser }"
            >
              <div v-if="msg.type === 'chat' || msg.type === 'text'" class="msg-content">
                <span class="msg-sender">{{ msg.nickname }}</span>
                <span class="msg-text">{{ msg.message }}</span>
                <span class="msg-time">{{ msg.time }}</span>
              </div>

              <div v-else-if="msg.type === 'image'" class="msg-content">
                <span class="msg-sender">{{ msg.nickname }}</span>
                 <ImageZoom :src="msg.imageData" alt="圖片訊息" />
                <span class="msg-time">{{ msg.time }}</span>
              </div>

              <span v-else>
                {{ msg.message }}
              </span>
            </li>
          </ul>
          
          <form @submit.prevent="sendMessage" class="input-area">
            <input 
              v-model="inputMessage" 
              type="text" 
              placeholder="輸入訊息..." 
              class="input-field"
              :disabled="!isJoined" 
            />
            <button type="submit" class="btn send-btn" :disabled="!isJoined">傳送</button>

            <label class="btn upload-btn">
              ＋
              <input 
                type="file" 
                accept="image/*" 
                @change="handleImageUpload" 
                style="display: none;" 
                :disabled="!isJoined"
              />
            </label>
          </form>
        </div>

        <div class="member-area">
          <h3>在線成員 ({{ members.length }})</h3>
          <ul>
            <li v-for="(member, index) in members" :key="index">
              {{ member }}
            </li>
          </ul>
        </div>
      </div>
    </div>

    <div v-if="!isJoined" class="login-overlay">
      <div class="login-box">
        <h2>{{ isRegisterMode ? '註冊帳號' : '使用者登入' }}</h2>
        
        <form @submit.prevent="handleAuth">
          
          <input 
            v-model="form.username" 
            type="text" 
            placeholder="帳號 (Username)" 
            required 
            class="input-field"
          />
          
          <input 
            v-model="form.password" 
            type="password" 
            placeholder="密碼 (Password)" 
            required 
            class="input-field"
          />
          
          <button type="submit" class="btn">
            {{ isRegisterMode ? '註冊並返回登入' : '登入聊天室' }}
          </button>

          <div class="toggle-mode">
            <span v-if="!isRegisterMode">還沒有帳號？ <a @click.prevent="isRegisterMode = true" href="#">去註冊</a></span>
            <span v-else>已經有帳號了？ <a @click.prevent="isRegisterMode = false" href="#">直接登入</a></span>
          </div>
          
          <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
        </form>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, nextTick, onBeforeUnmount } from 'vue'
import ImageZoom from '../components/ImageZoom.vue'

// --- 狀態變數 ---
const isJoined = ref(false)
const isRegisterMode = ref(false) // 控制現在是 "登入" 還是 "註冊" 介面
const errorMessage = ref('')

// 表單資料
const form = reactive({
  username: '',
  password: ''
})

const currentUser = ref('') // 登入後的使用者名稱
const token = ref('')       // JWT Token

const inputMessage = ref('')
const messages = ref([])
const members = ref([]) 
const messagesContainer = ref(null)

let ws = null
const API_URL = 'http://localhost:8000' // 後端 API 位址

// --- [核心邏輯] 處理 註冊 或 登入 ---
const handleAuth = async () => {
  errorMessage.value = '' // 清空錯誤訊息

  try {
    if (isRegisterMode.value) {
      // === 註冊流程 ===
      const res = await fetch(`${API_URL}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || '註冊失敗')
      }

      alert('註冊成功！請登入')
      isRegisterMode.value = false // 切換回登入模式
      // 不清除 form.username 和 password，方便使用者直接按登入

    } else {
      // === 登入流程 ===
      const res = await fetch(`${API_URL}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      })

      if (!res.ok) {
        throw new Error('帳號或密碼錯誤')
      }

      const data = await res.json()
      // 登入成功，保存 Token 和 使用者名稱
      token.value = data.access_token
      currentUser.value = data.username
      
      // 開始連線 WebSocket
      connectWebSocket()
    }
  } catch (error) {
    errorMessage.value = error.message
  }
}

// --- WebSocket 連線 ---
const connectWebSocket = () => {
  if (!token.value) return

  // [修改] 網址不再傳 nickname，而是傳 token
  ws = new WebSocket(`ws://127.0.0.1:8000/ws?token=${token.value}`)

  ws.onopen = () => {
    isJoined.value = true
    errorMessage.value = ''
  }

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)

    if (data.type === 'history') {
      messages.value = data.messages
      scrollToBottom()
    } 
    else if (['chat', 'system', 'image'].includes(data.type)) {
      messages.value.push(data)
      scrollToBottom()
    } 
    else if (data.type === 'member_list_update') {
      members.value = data.members
    }
  }

  ws.onclose = (event) => {
    // 若不是主動登出 (isJoined 為 true 代表是被動斷線)
    if (isJoined.value) {
      if (event.code === 4003) {
        alert("驗證失敗或重複登入")
      } else if (event.code !== 1000) {
        console.log("連線中斷")
      }
    }
    
    // 重置狀態
    isJoined.value = false
    messages.value = []
    members.value = []
  }
}

// --- [新增] 登出功能 ---
const logout = () => {
  if (ws) {
    isJoined.value = false // 先設為 false 避免觸發斷線 alert
    ws.close()
  }
  token.value = ''
  currentUser.value = ''
  form.username = ''
  form.password = ''
  messages.value = []
  members.value = []
}

const sendMessage = () => {
  if (ws && ws.readyState === WebSocket.OPEN && inputMessage.value.trim()) {
    ws.send(inputMessage.value)
    inputMessage.value = ''
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

onBeforeUnmount(() => {
  if (ws) ws.close()
})

const handleImageUpload = (event) => {
  const file = event.target.files[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = () => {
    const base64 = reader.result
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: "image",
        imageData: base64,
      }))
    }
  }
  reader.readAsDataURL(file)
}

</script>

<style scoped>
/* 樣式部分，新增了時間和訊息排版 */
/* 容器：設為全螢幕，移除 padding 和置中 */
.container {
  font-family: 'Segoe UI', sans-serif;
  width: 100vw;       /* 螢幕全寬 */
  height: 100vh;      /* 螢幕全高 */
  margin: 0;
  padding: 0;         /* 移除內距，讓它貼齊邊緣 */
  display: flex;
  justify-content: center;
  align-items: center;
  /* 這裡改用漸層背景，看起來更有質感 */
  background: linear-gradient(135deg, #e0e7ff 0%, #f0f9ff 100%);
  overflow: hidden;   /* 關鍵：防止內容溢出導致外層捲軸 */
}

/* --- 登入視窗相關 --- */
.login-box {
  background: white;
  width: 100%;
  max-width: 380px; /* 視窗寬度 */
  border-radius: 12px; /* 圓角 */
  /* 關鍵：利用強烈的陰影創造「浮起來」的感覺 */
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15), 0 5px 15px rgba(0,0,0,0.05);
  overflow: hidden; /* 確保內容不會凸出圓角 */
  
  /* 初始動畫：讓視窗有個輕微往下浮現的效果 */
  animation: modalPop 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
  border: 1px solid rgba(255,255,255,0.8);
  z-index: 101;
}

/* 視窗標題列 (Header) */
.login-box h2 {
  margin: 0;
  padding: 20px;
  font-size: 1.2rem;
  color: #334155;
  background: #f8fafc; /* 標題列顏色通常比較淺 */
  border-bottom: 1px solid #e2e8f0; /* 分隔線 */
  text-align: center;
  font-weight: 600;
  letter-spacing: 1px;
}

/* 內容表單區域 */
.login-box form {
  padding: 30px;
  display: flex;
  flex-direction: column;
  gap: 15px; /* 欄位之間的間距 */
}

/* 輸入框美化 */
.login-box .input-field {
  width: 100%;
  padding: 12px 15px;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 1rem;
  transition: all 0.3s ease;
  outline: none;
  background: #f8fafc;
}

.login-box .input-field:focus {
  border-color: #4ade80;
  background: white;
  box-shadow: 0 0 0 3px rgba(74, 222, 128, 0.2);
}

/* 按鈕美化 */
.login-box .btn {
  width: 100%;
  padding: 12px;
  font-size: 1rem;
  border-radius: 8px;
  background: #4ade80;
  color: white; /* 確保文字顏色 */
  font-weight: bold; /* 加粗 */
  box-shadow: 0 4px 6px -1px rgba(74, 222, 128, 0.4);
  transition: transform 0.1s, box-shadow 0.1s;
  border: none;
  cursor: pointer;
}

.login-box .btn:active {
  transform: scale(0.98); /* 點擊時微縮 */
}

/* [新增] 切換模式連結樣式 */
.toggle-mode {
  text-align: center;
  font-size: 0.9rem;
  color: #64748b;
  margin-top: 5px;
}

.toggle-mode a {
  color: #4ade80;
  text-decoration: none;
  font-weight: 600;
  cursor: pointer;
}

.toggle-mode a:hover {
  text-decoration: underline;
}

/* [新增] 錯誤訊息樣式 */
.error-text {
  color: #ef4444;
  font-size: 0.85rem;
  text-align: center;
  margin: 0;
}

/* 彈出動畫 Keyframes */
@keyframes modalPop {
  0% {
    opacity: 0;
    transform: translateY(-100px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* --- 聊天室主介面 --- */
.chat-ui {
  width: 100%;
  height: 100%;
  background: white;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 16px; /* 圓角 */
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
  transition: filter 0.5s ease;
  filter: blur(0);
  /* 如果你想讓聊天室也像視窗一樣浮在中間，可以保留這兩行；若要全螢幕則拿掉 */
  max-width: 90vw;
  height: 95vh;
}

/* 當沒登入時，聊天室變模糊 */
.chat-ui.blurred {
  filter: blur(8px) grayscale(30%); /* 模糊 8px，並稍微去色讓焦點集中在登入框 */
  pointer-events: none; /* 關鍵：禁止點擊背景的任何按鈕 */
  /* transform: scale(1.02); 稍微放大一點點，避免模糊導致邊緣露白 */
  transition: filter 0.5s ease; /* 登入成功時，慢慢變清晰的動畫 */
}

/* 登入遮罩層 (全螢幕覆蓋) */
.login-overlay {
  position: absolute; /* 絕對定位，蓋在 container 上 */
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  
  display: flex;
  justify-content: center;
  align-items: center;
  
  background: rgba(0, 0, 0, 0.2); /* 稍微變暗，讓登入框更凸顯 */
  z-index: 100; /* 確保在最上層 */
  
  /* 進場動畫 */
  animation: fadeIn 0.5s;
}

/* Header：改用白色簡約風，加上陰影與模糊效果 */
.header {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px); /* 毛玻璃特效 */
  color: #1e293b; /* 深灰藍色字體 */
  padding: 15px 25px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f1f5f9;
  /* z-index: 10; 確保浮在訊息上面 */
}

.header h1 {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0;
  color: #0f172a;
}

.user-badge {
  background: #e2e8f0;
  color: #475569;
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
}

/* [新增] 登出按鈕樣式 */
.logout-btn {
  background: #fee2e2;
  color: #ef4444;
  border: 1px solid #fecaca;
  padding: 5px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.logout-btn:hover {
  background: #fecaca;
}

/* 中間區域 */
.main-area {
  display: flex;
  flex: 1;
  overflow: hidden;
  background-color: #f8fafc; /* 非常淡的灰藍色背景 */
}

/* 聊天訊息區：左側 */
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
}

/* 訊息列表 */
.messages-list {
  flex: 1;
  list-style: none;
  padding: 20px;
  margin: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 15px; /* 訊息之間的間距 */
}

/* --- 訊息氣泡優化 (關鍵) --- */
.messages-list li {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 18px; /* 更大的圓角 */
  font-size: 0.95rem;
  line-height: 1.5;
  position: relative;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05); /* 輕微陰影代替邊框 */
  width: fit-content;
  margin: 0; /* reset */
}

/* 對方的訊息：白底 + 陰影 */
.messages-list li:not(.system-msg):not(.my-msg) {
  background: white;
  border-bottom-left-radius: 4px; /* 讓氣泡有個「尾巴」的感覺 */
  color: #334155;
}

/* 我的訊息：漸層綠/藍 + 白字 */
.messages-list li.my-msg {
  align-self: flex-end;
  /* 漂亮的漸層綠色，呼應你的登入按鈕 */
  background: linear-gradient(135deg, #4ade80 0%, #22c55e 100%);
  color: white;
  border-bottom-right-radius: 4px; /* 尾巴在右邊 */
  box-shadow: 0 4px 12px rgba(34, 197, 94, 0.2); /* 綠色光暈 */
}

/* 系統訊息：保持乾淨 */
.messages-list li.system-msg {
  align-self: center;
  background: rgba(0,0,0,0.03);
  color: #94a3b8;
  font-size: 0.8rem;
  padding: 5px 15px;
  border-radius: 20px;
  box-shadow: none;
}

/* .msg-content { display: flex; flex-direction: column; } */

/* 訊息內的文字細節 */
.msg-sender {
  font-size: 0.75rem;
  margin-bottom: 4px;
  opacity: 0.7; /* 稍微透明 */
  display: block;
}

.msg-text { font-size: 1em; line-height: 1.4; }

.msg-time {
  font-size: 0.7rem;
  opacity: 0.6;
  margin-top: 5px;
  display: block;
  text-align: right;
}

/* 右側：成員列表 (讓它看起來像個面板) */
.member-area {
  width: 240px;
  background: white;
  border-left: 1px solid #f1f5f9;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.member-area h3 {
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #94a3b8;
  margin-bottom: 15px;
  border-bottom: none;
}

.member-area ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.member-area li {
  padding: 10px;
  border-radius: 8px;
  color: #475569;
  font-weight: 500;
  display: flex;
  align-items: center;
  transition: background 0.2s;
}

.member-area li:hover {
  background: #f8fafc;
}

/* 在成員名字前加個小綠點，表示在線 */
.member-area li::before {
  content: '';
  display: inline-block;
  width: 8px;
  height: 8px;
  background: #4ade80;
  border-radius: 50%;
  margin-right: 10px;
}

/* --- 輸入區域：懸浮膠囊風格 --- */
.input-area {
  background: white;
  padding: 20px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  align-items: center;
  gap: 10px;
}

.input-field {
  flex: 1;
  padding: 12px 20px;
  background: #f1f5f9; /* 淺灰底色 */
  border: 1px solid transparent;
  border-radius: 24px; /* 膠囊狀 */
  font-size: 0.95rem;
  transition: all 0.3s;
}

.input-field:focus {
  background: white;
  border-color: #4ade80;
  box-shadow: 0 0 0 3px rgba(74, 222, 128, 0.1);
  outline: none;
}

/* .btn { padding: 10px 20px; background: #4ade80; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; } */
.btn:hover { background: #22c55e; }

/* 傳送按鈕：圓形或圓角 */
.send-btn {
  border: none;
  border-radius: 24px;
  padding: 10px 25px;
  background: #10b981;
  color: white;
  font-weight: bold;
  cursor: pointer;
  box-shadow: 0 4px 10px rgba(16, 185, 129, 0.2);
  transition: transform 0.1s;
}

.send-btn:active {
  transform: scale(0.95);
}

.upload-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #f1f5f9;
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: 0.2s;
  font-size: 1.2rem;
  margin: 0; /* Reset */
  border: none;
}

.upload-btn:hover {
  background: #e2e8f0;
  color: #334155;
}

</style>

<style>
body {
  margin: 0;            /* 移除瀏覽器預設邊距 */
  padding: 0;
  overflow: hidden;     /* 隱藏最外層的捲軸，只允許聊天室內部捲動 */
  width: 100vw;
  height: 100vh;
}

/* 確保 padding 不會讓寬度膨脹 */
*, *::before, *::after {
  box-sizing: border-box;
}
</style>