<template>
  <div class="container">
    <div v-if="!isJoined" class="login-box">
      <h2>加入聊天室</h2>
      <form @submit.prevent="joinChat">
        <input 
          v-model="nickname" 
          type="text" 
          placeholder="請輸入暱稱" 
          required 
          class="input-field"
        />
        <button type="submit" class="btn">加入</button>
      </form>
    </div>

    <div v-else class="chat-ui">
      <div class="header">
        <h1>聊天室</h1>
        <span class="user-badge">我是: {{ nickname }}</span>
      </div>

      <div class="main-area">
        <div class="chat-area">
          <ul ref="messagesContainer" class="messages-list">
            <li 
              v-for="(msg, index) in messages" 
              :key="index"
              :class="{ 'system-msg': msg.type === 'system' }"
            >
              <span v-if="msg.type === 'chat'">
                <strong>{{ msg.nickname }}:</strong> {{ msg.message }}
              </span>
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
            />
            <button type="submit" class="btn send-btn">傳送</button>
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
  </div>
</template>

<script setup>
import { ref, nextTick, onBeforeUnmount } from 'vue'

// --- 狀態變數 (State) ---
const nickname = ref('')
const inputMessage = ref('')
const isJoined = ref(false)
const messages = ref([]) // 儲存聊天紀錄
const members = ref([])  // 儲存成員列表
const messagesContainer = ref(null) // 用來控制滾動條的 DOM 元素

// WebSocket 實例
let ws = null

// --- 功能邏輯 ---

// 1. 加入聊天室
const joinChat = () => {
  if (!nickname.value.trim()) return

  // 連線到 FastAPI 後端
  // 注意：這裡直接連到後端的 IP:PORT
  ws = new WebSocket(`ws://127.0.0.1:8000/ws?nickname=${encodeURIComponent(nickname.value)}`)

  ws.onopen = () => {
    console.log('已連線')
    isJoined.value = true
  }

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    handleMessage(data)
  }

  ws.onclose = () => {
    alert('連線已中斷')
    isJoined.value = false
    messages.value = []
    members.value = []
  }
  
  ws.onerror = (err) => {
    console.error('WebSocket Error:', err)
  }
}

// 2. 處理接收到的訊息
const handleMessage = (data) => {
  if (data.type === 'chat' || data.type === 'system') {
    // 新增訊息到列表
    messages.value.push(data)
    // 收到新訊息後，自動滾動到底部
    scrollToBottom()
  } else if (data.type === 'member_list_update') {
    // 更新成員列表
    members.value = data.members
  }
}

// 3. 傳送訊息
const sendMessage = () => {
  if (ws && ws.readyState === WebSocket.OPEN && inputMessage.value.trim()) {
    ws.send(inputMessage.value)
    inputMessage.value = ''
  }
}

// 4. 自動滾動到底部 (UX 優化)
const scrollToBottom = async () => {
  // 使用 nextTick 確保 DOM 已經更新完畢後才執行滾動
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 5. 元件銷毀前關閉連線
onBeforeUnmount(() => {
  if (ws) ws.close()
})
</script>

<style scoped>
/* 簡單的 CSS 美化，類似之前的風格 */
.container {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  display: flex;
  justify-content: center;
  min-height: 90vh;
  align-items: center;
}

.login-box {
  background: #f9f9f9;
  padding: 40px;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  text-align: center;
}

.chat-ui {
  width: 100%;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.header {
  background: #4ade80; /* Nuxt Green */
  color: white;
  padding: 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.main-area {
  display: flex;
  height: 400px;
}

.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e0e0e0;
}

.messages-list {
  flex: 1;
  list-style: none;
  padding: 15px;
  margin: 0;
  overflow-y: auto;
  background: #f8fafc;
}

.messages-list li {
  margin-bottom: 8px;
  padding: 8px 12px;
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.messages-list li.system-msg {
  background: transparent;
  color: #888;
  font-style: italic;
  text-align: center;
  box-shadow: none;
  font-size: 0.9em;
}

.member-area {
  width: 200px;
  background: #fff;
  padding: 15px;
}

.member-area h3 {
  margin-top: 0;
  font-size: 1rem;
  border-bottom: 2px solid #eee;
  padding-bottom: 10px;
}

.input-area {
  display: flex;
  padding: 15px;
  background: white;
  border-top: 1px solid #e0e0e0;
}

.input-field {
  flex: 1;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-right: 10px;
}

.btn {
  padding: 10px 20px;
  background: #4ade80;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

.btn:hover {
  background: #22c55e;
}
</style>
<!-- <template>
  <div>
    <NuxtRouteAnnouncer />
    <NuxtWelcome />
  </div>
</template> -->
