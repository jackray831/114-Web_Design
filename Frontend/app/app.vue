<template>
  <div class="container">
    
    <div class="chat-ui" :class="{ 'blurred': !isJoined || isChangePasswordOpen }">
      <div class="header">
        <h1>聊天室</h1>
        
        <div class="header-right">
          <span class="user-badge">我是: {{ isJoined ? currentUser : '未登入' }}</span>
          
          <div v-if="isJoined" class="menu-container">
            
            <button @click="toggleMenu" class="menu-btn" :class="{ active: showMenu }">
              ⋮
            </button>

            <Transition name="menu-slide">
              <div v-if="showMenu" class="dropdown-menu">
                <div class="menu-header-info">帳號設定</div>
                <button @click="openChangePassword" class="dropdown-item">
                  更改密碼
                </button>
                <button @click="logout" class="dropdown-item logout-item">
                  登出
                </button>
              </div>
            </Transition>
            
            <div v-if="showMenu" @click="showMenu = false" class="menu-backdrop"></div>
          </div>
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
                 <ImageZoom :src="getFullImageUrl(msg.imageData)" alt="圖片訊息" />
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

    <Transition name="pop" appear>
      <div v-if="!isJoined" class="login-overlay" @click="triggerBounce">
        <div class="login-box" :class="{ 'bounce-active': isBouncing }" @click.stop>
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

            <input 
              v-if="isRegisterMode"
              v-model="form.confirmPassword" 
              type="password" 
              placeholder="請再次輸入密碼" 
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
    </Transition>

    <Transition name="pop" appear>
      <div v-if="isChangePasswordOpen" class="login-overlay" @click="triggerBounce">
        <div class="login-box" :class="{ 'bounce-active': isBouncing }" @click.stop>
          <div style="position: relative;">
            <h2>更改密碼</h2>
            <button @click="closeChangePassword" class="close-btn">✕</button>
          </div>
          
          <form @submit.prevent="submitChangePassword">
            <input 
              v-model="passwordForm.oldPassword" 
              type="password" 
              placeholder="舊密碼" 
              required 
              class="input-field"
            />
            
            <input 
              v-model="passwordForm.newPassword" 
              type="password" 
              placeholder="新密碼 (至少8碼含英數)" 
              required 
              class="input-field"
            />

            <input 
              v-model="passwordForm.confirmNewPassword" 
              type="password" 
              placeholder="確認新密碼" 
              required 
              class="input-field"
            />
            
            <button type="submit" class="btn">確認修改</button>
            
            <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
          </form>
        </div>
      </div>
    </Transition>

  </div>
</template>

<script setup>
import { ref, reactive, nextTick, onBeforeUnmount } from 'vue'
import ImageZoom from '../components/ImageZoom.vue'

// --- 狀態變數 ---
const isJoined = ref(false)
const isRegisterMode = ref(false) // 控制現在是 "登入" 還是 "註冊" 介面
const isChangePasswordOpen = ref(false)
const isBouncing = ref(false)
const errorMessage = ref('')
const showMenu = ref(false)

// 表單資料 - 登入/註冊
const form = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

// 表單資料 - 修改密碼
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmNewPassword: ''
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

      // [新增] 前端先簡單檢查一下，提升使用者體驗
      if (form.password !== form.confirmPassword) {
        throw new Error("兩次密碼輸入不一致")
      }
      
      // 準備要傳給後端的資料 (需包含 confirm_password)
      const registerPayload = {
        username: form.username,
        password: form.password,
        confirm_password: form.confirmPassword
      }

      const res = await fetch(`${API_URL}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(registerPayload)
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || '註冊失敗')
      }

      alert('註冊成功！請登入')
      isRegisterMode.value = false // 切換回登入模式
      // 清空密碼欄位避免混淆
      form.password = ''
      form.confirmPassword = ''

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

// [新增] 切換選單顯示/隱藏
const toggleMenu = () => {
  showMenu.value = !showMenu.value
}

// [新增] 開啟更改密碼視窗 (並關閉下拉選單)
const openChangePassword = () => {
  showMenu.value = false // 關閉下拉選單
  isChangePasswordOpen.value = true // 開啟視窗
  // 清空表單
  passwordForm.oldPassword = ''
  passwordForm.newPassword = ''
  passwordForm.confirmNewPassword = ''
  errorMessage.value = ''
}

// [新增] 關閉更改密碼視窗
const closeChangePassword = () => {
  isChangePasswordOpen.value = false
  errorMessage.value = ''
}

// [新增] 觸發彈跳效果的函式
const triggerBounce = () => {
  // 如果正在彈跳中，就不重複觸發
  if (isBouncing.value) return

  isBouncing.value = true
  
  // 設定與 CSS 動畫時間相同的延遲 (0.3s = 300ms)，動畫結束後移除 class
  setTimeout(() => {
    isBouncing.value = false
  }, 300)
}

// [新增] 送出更改密碼請求
const submitChangePassword = async () => {
  errorMessage.value = ''
  
  if (passwordForm.newPassword !== passwordForm.confirmNewPassword) {
    errorMessage.value = "兩次新密碼輸入不一致"
    return
  }

  try {
    const res = await fetch(`${API_URL}/change-password`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token.value}` // 記得帶上 Token
      },
      body: JSON.stringify({
        old_password: passwordForm.oldPassword,
        new_password: passwordForm.newPassword,
        confirm_new_password: passwordForm.confirmNewPassword
      })
    })

    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '修改失敗')
    }

    alert('密碼修改成功！')
    closeChangePassword()

  } catch (error) {
    errorMessage.value = error.message
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
  form.confirmPassword = '' // 記得清空確認密碼
  messages.value = []
  members.value = []
  showMenu.value = false
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

// [新增] 處理圖片路徑的輔助函式
// 目的：把後端回傳的 "/static/uploads/..." 轉成 "http://localhost:8000/static/uploads/..."
const getFullImageUrl = (path) => {
  if (!path) return ''
  // 如果是舊的 Base64 資料 (開頭是 data:image)，直接回傳
  if (path.startsWith('data:image')) return path
  // 如果已經是完整的 http 開頭網址，直接回傳
  if (path.startsWith('http')) return path
  
  // 否則，補上後端 API 的 Domain
  return `${API_URL}${path}`
}

// [修改] 上傳圖片並發送訊息
const handleImageUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  // 1. 建立 FormData
  const formData = new FormData()
  // 注意：這裡的 'file' 必須對應後端 @app.post("/upload") 裡的參數名稱
  formData.append('file', file)

  try {
    // 2. 透過 HTTP POST 上傳圖片
    const res = await fetch(`${API_URL}/upload`, {
      method: 'POST',
      body: formData // fetch 會自動設定 multipart/form-data
    })

    if (!res.ok) {
      throw new Error('圖片上傳失敗')
    }

    const data = await res.json()
    // 預期後端回傳: { "url": "/static/uploads/uuid-filename.jpg" }
    const imageUrl = data.url

    // 3. 上傳成功後，透過 WebSocket 發送「圖片網址」
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: "image",
        imageData: imageUrl, // 這裡傳送的是短短的路徑字串
      }))
    }

  } catch (error) {
    console.error(error)
    alert("圖片傳送失敗，請稍後再試")
  } finally {
    // 清空 input，這樣才能重複選取同一張圖片
    event.target.value = ''
  }
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
  border: 1px solid rgba(255,255,255,0.8);
  z-index: 101;
  transform-origin: center;
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

/* --- 聊天室主介面 --- */
.chat-ui {
  width: 100%;
  background: white;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 16px; /* 圓角 */
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
  transition: filter 0.5s ease;
  filter: blur(0);
  max-width: 90vw;
  height: 95vh;
}

/* 當沒登入時，聊天室變模糊 */
.chat-ui.blurred {
  filter: blur(8px) grayscale(30%); /* 模糊 8px，並稍微去色讓焦點集中在登入框 */
  pointer-events: none; /* 關鍵：禁止點擊背景的任何按鈕 */
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
  
  background: rgba(0, 0, 0, 0.5); /* 稍微變暗，讓登入框更凸顯 */
  z-index: 100; /* 確保在最上層 */
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

/* --- Header 右側容器微調 --- */
.header-right {
  display: flex;
  align-items: center;
  gap: 15px; /* 拉開名字與選單按鈕的距離 */
}

/* --- 選單容器 (相對定位，作為下拉選單的參考點) --- */
.menu-container {
  position: relative;
  display: flex;
  align-items: center;
}

/* --- 選單觸發按鈕 (三點) --- */
.menu-btn {
  background: transparent;
  border: none;
  font-size: 1.5rem;
  line-height: 1;
  color: #64748b;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
  font-weight: bold;
}

.menu-btn:hover, .menu-btn.active {
  background-color: #f1f5f9;
  color: #1e293b;
}

/* --- 下拉選單本體 --- */
.dropdown-menu {
  position: absolute;
  top: 120%; /* 在按鈕下方一點點 */
  right: 0;   /* 靠右對齊 */
  width: 160px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  border: 1px solid #f1f5f9;
  padding: 6px;
  z-index: 50; /* 確保浮在最上層 */
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* 選單內的小標題 */
.menu-header-info {
  font-size: 0.75rem;
  color: #94a3b8;
  padding: 8px 12px;
  border-bottom: 1px solid #f1f5f9;
  margin-bottom: 4px;
}

/* 選單內的按鈕 */
.dropdown-item {
  text-align: left;
  background: transparent;
  border: none;
  padding: 10px 12px;
  font-size: 0.9rem;
  color: #334155;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
  width: 100%;
}

.dropdown-item:hover {
  background-color: #f8fafc;
}

/* 特製登出按鈕樣式 */
.dropdown-item.logout-item {
  color: #ef4444; /* 紅色文字 */
}

.dropdown-item.logout-item:hover {
  background-color: #fef2f2; /* 淺紅色背景 */
}

/* --- 透明遮罩 (點擊外部關閉選單用) --- */
.menu-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 49; /* 比選單低一層，但比其他內容高 */
  cursor: default;
}

.user-badge {
  background: #e2e8f0;
  color: #475569;
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
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
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 18px; /* 更大的圓角 */
  font-size: 1rem;
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

.msg-text { 
  font-size: 1em;
  line-height: 1.4;
}

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

/* 視窗右上角的關閉按鈕 */
.close-btn {
  position: absolute;
  right: 15px;
  top: 15px;
  background: transparent;
  border: none;
  font-size: 1.2rem;
  color: #94a3b8;
  cursor: pointer;
  z-index: 10;
}
.close-btn:hover {
  color: #475569;
}

/* --- 動畫效果 --- */
.pop-enter-active,
.pop-leave-active {
  transition: opacity 0.5s ease;
}
.pop-enter-from,
.pop-leave-to {
  opacity: 0;
}
.pop-enter-active .login-box {
  animation: modalPop 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}
.pop-leave-active .login-box {
  animation: modalClose 0.3s ease-in forwards;
}
.bounce-active {
  animation: bounce 0.3s cubic-bezier(0.36, 0.07, 0.19, 0.97) forwards;
}
.menu-slide-enter-active,
.menu-slide-leave-active {
  transition: all 0.2s ease-out;
  transform-origin: top right; /* 關鍵：讓動畫從右上角(按鈕處)開始縮放 */
}
.menu-slide-enter-from,
.menu-slide-leave-to {
  opacity: 0;
  transform: scale(0.8) translateY(-5px); /* 稍微縮小並往上移 */
}
.menu-slide-enter-to,
.menu-slide-leave-from {
  opacity: 1;
  transform: scale(1) translateY(0);
}
@keyframes bounce {
  0% { transform: scale(1); }
  40% { transform: scale(1.02); } /* 稍微放大 */
  75% { transform: scale(0.99); } /* 稍微縮過頭 */
  100% { transform: scale(1); }   /* 回復原狀 */
}
@keyframes modalPop {
  0% { opacity: 0; transform: translateY(-100px); }
  100% { opacity: 1; transform: translateY(0); }
}
@keyframes modalClose {
  0% { opacity: 1; transform: translateY(0); }
  100% { opacity: 0; transform: translateY(-100px); }
}
@keyframes menuFadeIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
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

.medium-zoom-overlay {
  backdrop-filter: blur(5px); /* 背景模糊效果 */
}
</style>