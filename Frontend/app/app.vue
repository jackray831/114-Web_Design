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

            <div 
              v-if="messages.length >= 300 && !historyEndReached" 
              style="text-align: center; margin: 15px 0;"
            >
              <button 
                @click="loadMoreHistory"
                class="load-more-btn"
                :disabled="isLoadingHistory"
              >
                {{ isLoadingHistory ? '載入中...' : '載入更早的訊息' }}
              </button>
            </div>

            <li 
              v-for="(msg, index) in processedMessages" 
              :key="msg.id || index"
              :class="{ 'system-msg': msg.type === 'system', 'my-msg': msg.nickname === currentUser }"
            >
              <div v-if="msg.type === 'chat' || msg.type === 'text'" class="msg-content">
                <span class="msg-sender">{{ msg.nickname }}</span>
                <span class="msg-text" v-html="linkify(msg.message)"></span>
                <span class="msg-time">{{ getMessageTime(msg.time) }}</span>
              </div>

              <div v-else-if="msg.type === 'image'" class="msg-content">
                <span class="msg-sender">{{ msg.nickname }}</span>
                 <ImageZoom :src="getFullImageUrl(msg.imageData)" alt="圖片訊息" />
                <span class="msg-time">{{ getMessageTime(msg.time) }}</span>
              </div>
              
              <div v-else-if="msg.type === 'video'" class="msg-content">
                <span class="msg-sender">{{ msg.nickname }}</span>
                <video 
                  :src="getFullImageUrl(msg.imageData)" 
                  controls 
                  style="max-width: 300px; border-radius: 8px; margin-top: 5px;" 
                />
                <span class="msg-time">{{ getMessageTime(msg.time) }}</span>
              </div>

              <div v-else-if="msg.type === 'file'" class="msg-content">
                <span class="msg-sender">{{ msg.nickname }}</span>
                <a :href="getFullImageUrl(msg.imageData)" download target="_blank" class="chat-link">
                  {{ msg.filename || '檔案下載' }}
                </a>
                <span class="msg-time">{{ getMessageTime(msg.time) }}</span>
              </div>

              <span v-else>
                {{ msg.message }}
              </span>
            </li>
          </ul>
          
          <form @submit.prevent="sendMessage" class="input-area">
            <input 
              ref="chatInputRef"
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
                accept=".jpg,.jpeg,.png,.gif,.pdf,.doc,.docx,.zip,.rar,.mp4,.webm"  
                @change="handleFileUpload" 
                style="display: none;" 
                :disabled="!isJoined"
              />
            </label>
          </form>
        </div>

        <div class="member-area">
          <h3 class="status-title online">線上 ({{ members.length }})</h3>
          <ul class="member-list">
            <li v-for="(member, index) in members" :key="'on-'+index">
              {{ member }}
            </li>
          </ul>

          <div v-if="offlineMembers.length > 0" style="margin-top: 20px;">
            <h3 class="status-title offline">
              離線 ({{ offlineMembers.length }})
            </h3>
            <ul class="member-list offline-list">
              <li v-for="(member, index) in offlineMembers" :key="'off-'+index">
                {{ member }}
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <Transition name="pop" appear>
      <div v-if="!isJoined" class="login-overlay" @click="triggerBounce">
        <div class="login-box" :class="{ 'bounce-active': isBouncing }" v-shake="errorMessage" @click.stop>
          <Transition 
            :name="isRegisterMode ? 'slide-left' : 'slide-right'" 
            mode="out-in"
          >
            <div :key="isRegisterMode" class="auth-container">
              <h2>{{ isRegisterMode ? '註冊帳號' : '使用者登入' }}</h2>
              
              <form @submit.prevent="handleAuth">
                
                <input 
                  v-focus
                  v-model="form.username" 
                  type="text" 
                  placeholder="帳號 (Username)" 
                  required 
                  class="input-field"
                  @input="errorMessage = ''"
                />
                
                <input 
                  v-model="form.password" 
                  type="password" 
                  placeholder="密碼 (Password)" 
                  required 
                  class="input-field"
                  @input="errorMessage = ''"
                />

                <input 
                  v-if="isRegisterMode"
                  v-model="form.confirmPassword" 
                  type="password" 
                  placeholder="請再次輸入密碼" 
                  required 
                  class="input-field"
                  @input="errorMessage = ''"
                />
                
                <button type="submit" class="btn" :disabled="isLoading">
                  <span v-if="isLoading">處理中...</span>
                  <span v-else>{{ isRegisterMode ? '註冊並返回登入' : '登入聊天室' }}</span>
                </button>

                <div class="toggle-mode">
                  <span v-if="!isRegisterMode">還沒有帳號？ <a @click.prevent="isRegisterMode = true; errorMessage = ''" href="#">去註冊</a></span>
                  <span v-else>已經有帳號了？ <a @click.prevent="isRegisterMode = false; errorMessage = ''" href="#">直接登入</a></span>
                </div>
                
                <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
              </form>
            </div>
          </Transition>
        </div>
      </div>
    </Transition>

    <Transition name="pop" appear>
      <div v-if="isChangePasswordOpen" class="login-overlay" @click="triggerBounce">
        <div class="login-box" :class="{ 'bounce-active': isBouncing }" v-shake="errorMessage" @click.stop>
          <div style="position: relative;">
            <h2>更改密碼</h2>
            <button @click="closeChangePassword" class="close-btn">✕</button>
          </div>
          
          <form @submit.prevent="submitChangePassword">
            <input 
              v-focus
              v-model="passwordForm.oldPassword" 
              type="password" 
              placeholder="舊密碼" 
              required 
              class="input-field"
              @input="errorMessage = ''"
            />
            
            <input 
              v-model="passwordForm.newPassword" 
              type="password" 
              placeholder="新密碼 (至少8碼含英數)" 
              required 
              class="input-field"
              @input="errorMessage = ''"
            />

            <input 
              v-model="passwordForm.confirmNewPassword" 
              type="password" 
              placeholder="確認新密碼" 
              required 
              class="input-field"
              @input="errorMessage = ''"
            />
            
            <button type="submit" class="btn" :disabled="isLoading">{{ isLoading ? '處理中...' : '確認修改' }}</button>
            
            <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
          </form>
        </div>
      </div>
    </Transition>

  </div>
</template>

<script setup>
import { ref, reactive, nextTick, onBeforeUnmount, watch, computed } from 'vue'
import ImageZoom from '../components/ImageZoom.vue'

// --- 狀態變數 ---
const isJoined = ref(false)
const isRegisterMode = ref(false) // 控制現在是 "登入" 還是 "註冊" 介面
const isChangePasswordOpen = ref(false)
const isBouncing = ref(false)
const isLoading = ref(false)
const isLoadingHistory = ref(false)
const historyEndReached = ref(false)
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
const allUsers = ref([])

const vFocus = { mounted: (el) => el.focus() }
const chatInputRef = ref(null)

let ws = null
const API_URL = 'http://localhost:8000' // 後端 API 位址

// 1. 日期格式化函式 (處理 今天/昨天/星期幾)
const formatSystemDate = (dateStr) => {
  if (!dateStr || dateStr.length < 10) return dateStr 

  const date = new Date(dateStr)
  const now = new Date()
  
  // 只比較日期部分 (設為當天 00:00:00)
  const targetDate = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today)
  yesterday.setDate(today.getDate() - 1)

  const weekDays = ['日', '一', '二', '三', '四', '五', '六']
  const weekDayStr = weekDays[date.getDay()]

  // 判斷邏輯
  if (targetDate.getTime() === today.getTime()) {
    return '今天'
  }
  if (targetDate.getTime() === yesterday.getTime()) {
    return '昨天'
  }
  if (date.getFullYear() === now.getFullYear()) {
    return `${date.getMonth() + 1}月${date.getDate()}日(${weekDayStr})`
  }
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日(${weekDayStr})`
}

// 2. 時間切割函式 (只顯示 18:30)
const getMessageTime = (fullTime) => {
  if (fullTime && fullTime.includes(' ')) {
    return fullTime.split(' ')[1].substring(0, 5) // 取 HH:MM
  }
  return fullTime
}

// 3. [核心修改] 加工後的訊息列表
// 這會自動在換日時插入一個 "type: system" 的訊息
const processedMessages = computed(() => {
  const result = []
  let lastDate = ''

  messages.value.forEach(msg => {
    // 取得日期部分 (YYYY-MM-DD)
    const currentDate = msg.time ? msg.time.split(' ')[0] : ''

    // 如果日期跟上一條不一樣，就插入一個 "假的" 系統訊息
    if (currentDate && currentDate !== lastDate && currentDate.includes('-')) {
      result.push({
        type: 'system',               // 直接用系統訊息類型
        message: formatSystemDate(msg.time), // 內容就是格式化後的日期
        nickname: '',                 // 系統訊息不需要暱稱
        time: ''                      // 系統訊息不需要時間
      })
      lastDate = currentDate
    }

    result.push(msg)
  })

  return result
})

// --- [新增] 計算離線成員 (所有成員 - 在線成員) ---
// 這裡的 members 是 WebSocket 傳來的「在線名單」
const offlineMembers = computed(() => {
  return allUsers.value.filter(user => !members.value.includes(user))
})

// --- [新增] 抓取所有成員的函式 ---
const fetchAllUsers = async () => {
  try {
    const res = await fetch(`${API_URL}/users`) // 呼叫剛加的後端 API
    if (res.ok) {
      allUsers.value = await res.json()
    }
  } catch (err) {
    console.error("無法取得成員列表", err)
  }
}

// [新增] 載入更多歷史訊息的函式
const loadMoreHistory = async () => {
  isLoadingHistory.value = true
  
  try {
    // 1. 計算目前已經顯示多少筆 (這就是我們要 skip 的數量)
    // 注意：我們要扣除掉前端自己產生的日期分隔線 (type: 'system')
    // 但為了簡單起見，直接用 messages.value.length (原始資料長度) 最準確
    const currentCount = messages.value.length
    const limit = 100
    
    // 2. 呼叫後端 API
    const res = await fetch(`${API_URL}/history/more?skip=${currentCount}&limit=${limit}`)
    const newOldMessages = await res.json()
    
    if (newOldMessages.length < limit) {
      historyEndReached.value = true
    }

    if (newOldMessages.length === 0) {
      return // 沒有更多訊息了
    }

    const container = messagesContainer.value
    const prevHeight = container.scrollHeight
    
    // 4. 把新抓到的舊訊息合併到陣列最前面
    messages.value = [...newOldMessages, ...messages.value]
    
    // 5. [關鍵體驗優化] 修正捲軸位置，讓畫面停在原本閱讀的地方
    await nextTick()
    container.scrollTop = container.scrollHeight - prevHeight
  } catch (err) {
    console.error("載入失敗", err)
    alert("無法載入歷史訊息")
  } finally {
    isLoadingHistory.value = false
  }
}

// --- [核心邏輯] 處理 註冊 或 登入 ---
const handleAuth = async () => {
  if (isLoading.value) return // 防止重複提交
  isLoading.value = true
  errorMessage.value = '' // 清空錯誤訊息

  try {
    if (isRegisterMode.value) {
      // === 註冊流程 ===
      
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

      // [新增] 登入成功後，立刻抓取所有成員名單
      fetchAllUsers()
      
      // 開始連線 WebSocket
      connectWebSocket()
    }
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isLoading.value = false
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
    else if (['chat', 'system', 'image', 'file', 'video'].includes(data.type)) {
      messages.value.push(data)
      scrollToBottom()
    } 
    else if (data.type === 'member_list_update') {
      members.value = data.members
      fetchAllUsers() // 更新所有成員列表
    }
  }

  ws.onclose = (event) => {
    // 若不是主動登出 (isJoined 為 true 代表是被動斷線)
    if (isJoined.value) {
      // [新增] 處理被踢下線的情況
      if (event.code === 4001) {
        alert("您的帳號已在其他裝置登入，本機連線已中斷。")
        logout() // 自動呼叫登出清理畫面
        return   // 結束，不執行下面的邏輯
      }

      if (event.code === 4003) {
        alert("驗證失敗，請重新登入。")
      } else if (event.code !== 1000) {
        console.log("連線異常中斷")
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

const vShake = (el, binding) => {
  // 只有當：
  // 1. 有錯誤訊息 (binding.value 為真)
  // 2. 且 錯誤訊息跟上次不一樣 (binding.value !== binding.oldValue)
  // 才會觸發搖動
  if (binding.value && binding.value !== binding.oldValue) {
    el.classList.remove('shake-active')
    void el.offsetWidth
    el.classList.add('shake-active')
  }
}

// [新增] 送出更改密碼請求
const submitChangePassword = async () => {
  if (isLoading.value) return // 防止重複提交
  errorMessage.value = ''
  isLoading.value = true
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
  } finally {
    isLoading.value = false
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

// --- [新增] 監聽登入狀態，登入成功後聚焦聊天框 ---
watch(isJoined, async (newVal) => {
  if (newVal) {
    await nextTick() // 等待 DOM 更新 (disable 屬性移除)
    chatInputRef.value?.focus()
  }
})

// 將文字中的網址轉成可點擊連結
const linkify = (text) => {
  if (!text) return ''

  const urlRegex = /(https?:\/\/[^\s]+)/g

  return text.replace(urlRegex, (url) => {
    return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="chat-link">${url}</a>`
  })
}

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

// [修改] 上傳檔案並發送訊息
const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)

  try {
    const res = await fetch(`${API_URL}/upload`, {
      method: 'POST',
      body: formData
    })

    if (!res.ok) throw new Error('檔案上傳失敗')

    const data = await res.json()
    const fileUrl = data.url

    // 根據副檔名判斷是否為圖片或影片
    const isImage = file.type.startsWith('image/')
    const isVideo = file.type.startsWith('video/')

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: isImage ? 'image' : (isVideo ? 'video' : 'file'),
        imageData: fileUrl,  // 後端統一回傳 /static/uploads/xxx.xxx
        filename: file.name
      }))
    }

  } catch (err) {
    alert(err.message || '上傳失敗')
  } finally {
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
  transition: all 0.3s ease;
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
  border: none;
  cursor: pointer;
  transition: background-color 0.3s ease, box-shadow 0.3s ease, transform 0.1s ease;
}

.login-box .btn:hover {
  background: #22c55e;
  box-shadow: 0 4px 6px -1px rgba(74, 222, 128, 0.4);
}

.login-box .btn:active {
  transform: scale(0.98); /* 點擊時微縮 */
  box-shadow: 0 2px 4px -1px rgba(74, 222, 128, 0.4);
}

.login-box .btn:disabled {
  background: #bdc3c7;
  color: #ffffff; /* 保持文字顏色，或者稍微變灰 */
  cursor: not-allowed;
  transform: scale(1);
  box-shadow: none;
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
  position: relative;
  z-index: 100; /* 確保浮在訊息上面 */
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

/* 聊天室網址樣式 */
.chat-link {
  color: #2563eb;          /* 藍色 */
  text-decoration: underline;
  word-break: break-all;   /* 避免長網址爆版 */
}

.chat-link:hover {
  color: #1d4ed8;
}

/* 右側：成員列表 (讓它看起來像個面板) */
.member-area {
  width: 240px;
  background: white;
  border-left: 1px solid #f1f5f9;
  padding: 20px;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  height: 100%;
}

.member-area h3 {
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #94a3b8;
  margin-bottom: 15px;
  border-bottom: none;
  display: flex;
  align-items: center;
  gap: 8px;
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

/* [選用] 美化捲軸 (Chrome/Safari/Edge) */
.member-area::-webkit-scrollbar {
  width: 6px;
}
.member-area::-webkit-scrollbar-track {
  background: transparent;
}
.member-area::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 3px;
}
/* 在線標題的小綠點 (選擇性) */
/* .status-title.online::before {
  content: '';
  display: block;
  width: 8px;
  height: 8px;
  background: #4ade80;
  border-radius: 50%;
} */

/* 離線標題的小灰點 (選擇性) */
/* .status-title.offline::before {
  content: '';
  display: block;
  width: 8px;
  height: 8px;
  background: #94a3b8; /* 灰色 */
  /* border-radius: 50%; */
/* } */

/* 共用的列表樣式 */
.member-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

/* 離線成員列表的樣式 */
.offline-list li {
  color: #94a3b8; /* 文字變淡 */
}

/* 覆寫原本 li::before 的綠點 */
/* 針對「離線列表」下的 li，把前面的點改成空心或灰色 */
.offline-list li::before {
  background: transparent; /* 變成透明背景 */
  border: 2px solid #cbd5e1; /* 加上灰色邊框 = 空心圓 */
  box-sizing: border-box;
}

/* 滑鼠移過去離線成員的效果 */
.offline-list li:hover {
  background: #f1f5f9;
  color: #64748b;
}

.load-more-btn {
  /* 1. 拿掉邊框與陰影，改用非常淡的背景色 */
  background-color: #f1f5f9; /* 非常淺的灰藍色 */
  border: none;
  box-shadow: none;
  
  /* 2. 文字顏色用深灰色，不要全黑 */
  color: #94a3b8; 
  
  /* 3. 維持圓角與間距 */
  padding: 6px 18px;
  border-radius: 20px;
  font-size: 0.85rem;
  
  cursor: pointer;
  transition: all 0.2s ease;
}

/* 滑鼠移上去時，才讓它稍微明顯一點 (像是在說：我可以按喔) */
.load-more-btn:hover {
  background-color: #e2e8f0; /* 背景稍微變深 */
  color: #475569;            /* 文字變深 */
}

.load-more-btn:active {
  background-color: #cbd5e1;
}

.load-more-btn:disabled {
  background-color: transparent;
  color: #cbd5e1;
  cursor: wait;
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
/* .btn:hover { background: #22c55e; } */

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
.slide-left-enter-active, .slide-left-leave-active,
.slide-right-enter-active, .slide-right-leave-active {
  transition: all 0.2s ease-in-out;
}
.slide-left-leave-to { opacity: 0; transform: translateX(-50px); }
.slide-left-enter-from { opacity: 0; transform: translateX(50px); }
.slide-right-leave-to { opacity: 0; transform: translateX(50px); }
.slide-right-enter-from { opacity: 0; transform: translateX(-50px); }

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
.shake-active {
  animation: shake 0.5s cubic-bezier(0.36, 0.07, 0.19, 0.97) both;
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
@keyframes shake {
  10%, 90% { transform: translate3d(-1px, 0, 0); }
  20%, 80% { transform: translate3d(2px, 0, 0); }
  30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
  40%, 60% { transform: translate3d(4px, 0, 0); }
}

/* RWD - 當螢幕寬度小於 768px (手機/平板直向) */
@media (max-width: 768px) {
  .member-area {
    display: none; /* 預設隱藏成員列表 */
    /* 或者改為 position: absolute 的側邊欄 */
  }
  
  .chat-ui {
    max-width: 100vw;
    height: 100vh;
    border-radius: 0; /* 手機版通常不需要圓角，佔滿全螢幕體驗較好 */
  }
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