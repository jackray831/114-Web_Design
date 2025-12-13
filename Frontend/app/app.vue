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
              :class="{ 'system-msg': msg.type === 'system', 'my-msg': msg.nickname === nickname }"
            >
              <div v-if="msg.type === 'chat' || msg.type === 'text'" class="msg-content">
                <span class="msg-sender">{{ msg.nickname }}</span>
                <span class="msg-text">{{ msg.message }}</span>
                <span class="msg-time">{{ msg.time }}</span>
              </div>

              <div v-else-if="msg.type === 'image'" class="msg-content">
                <span class="msg-sender">{{ msg.nickname }}</span>
                <!-- <img :src="msg.imageData" alt="圖片訊息" style="max-width: 200px; border-radius: 6px;" /> -->
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
            />
            <button type="submit" class="btn send-btn">傳送</button>

            <!-- 新增 + 圖片上傳按鈕 -->
            <label class="btn upload-btn">
              ＋
              <input type="file" accept="image/*" @change="handleImageUpload" style="display: none;" />
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
  </div>
</template>

<script setup>
import { ref, nextTick, onBeforeUnmount } from 'vue'
import ImageZoom from '../components/ImageZoom.vue'

const nickname = ref('')
const inputMessage = ref('')
const isJoined = ref(false)
const messages = ref([])
const members = ref([]) 
const messagesContainer = ref(null)

let ws = null

const joinChat = () => {
  if (!nickname.value.trim()) return

  ws = new WebSocket(`ws://127.0.0.1:8000/ws?nickname=${encodeURIComponent(nickname.value)}`)

  ws.onopen = () => {
    isJoined.value = true
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


  // 處理錯誤與斷線
  ws.onclose = (event) => {
    isJoined.value = false
    messages.value = []
    members.value = []
    
    // 檢查錯誤代碼 4003 (暱稱重複)
    if (event.code === 4003) {
      alert("這個暱稱已經有人使用了，請換一個！")
    } else {
      // 只有非正常關閉才跳出斷線提示
      if (event.code !== 1000 && event.code !== 1005) {
        alert("連線已中斷")
      }
    }
  }
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
.container { font-family: 'Segoe UI', sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; display: flex; justify-content: center; min-height: 90vh; align-items: center; }
.login-box { background: #f9f9f9; padding: 40px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }
.chat-ui { width: 100%; background: white; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.header { background: #4ade80; color: white; padding: 15px; display: flex; justify-content: space-between; align-items: center; }
.main-area { display: flex; height: 500px; }
.chat-area { flex: 1; display: flex; flex-direction: column; border-right: 1px solid #e0e0e0; }

.messages-list { flex: 1; list-style: none; padding: 15px; margin: 0; overflow-y: auto; background: #f1f5f9; }

/* 訊息樣式優化 */
.messages-list li { margin-bottom: 10px; padding: 8px 12px; border-radius: 8px; max-width: 80%; width: fit-content; }

/* 別人的訊息 (靠左) */
.messages-list li:not(.system-msg):not(.my-msg) { background: white; border: 1px solid #ddd; }

/* 我的訊息 (靠右，綠色) */
.messages-list li.my-msg { align-self: flex-end; background: #dcfce7; border: 1px solid #bbf7d0; margin-left: auto; }

/* 系統訊息 (置中，灰色) */
.messages-list li.system-msg { margin: 10px auto; background: transparent; color: #888; font-size: 0.85em; text-align: center; font-style: italic; box-shadow: none; width: 100%; max-width: 100%; }

.msg-content { display: flex; flex-direction: column; }
.msg-sender { font-weight: bold; font-size: 0.9em; margin-bottom: 2px; color: #333; }
.msg-text { font-size: 1em; line-height: 1.4; }
.msg-time { font-size: 0.7em; color: #999; align-self: flex-end; margin-top: 4px; }

.member-area { width: 200px; background: #fff; padding: 15px; }
.member-area h3 { margin-top: 0; font-size: 1rem; border-bottom: 2px solid #eee; padding-bottom: 10px; }
.input-area { display: flex; padding: 15px; background: white; border-top: 1px solid #e0e0e0; }
.input-field { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 4px; margin-right: 10px; }
.btn { padding: 10px 20px; background: #4ade80; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
.btn:hover { background: #22c55e; }
</style>