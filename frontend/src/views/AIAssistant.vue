<template>
  <div>
    <div
      v-if="visible && hasPermission"
      class="fixed bottom-6 left-[240px] z-50 transition-all duration-300"
      :class="{ 'opacity-100 scale-100': visible, 'opacity-0 scale-0': !visible }"
    >
      <div
        class="w-[420px] bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col overflow-hidden"
        style="max-height: 600px"
      >
        <div class="bg-gradient-to-r from-blue-500 to-indigo-600 px-5 py-4 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center text-2xl">
              🤖
            </div>
            <div>
              <h3 class="text-white font-semibold text-base">AI 助手</h3>
              <p class="text-blue-100 text-xs">E9 Payroll 智能助手</p>
            </div>
          </div>
          <button
            class="text-white/80 hover:text-white transition-colors text-xl leading-none"
            @click="visible = false"
          >
            ✕
          </button>
        </div>

        <div ref="chatBody" class="flex-1 overflow-y-auto px-4 py-4 space-y-3 bg-gray-50" style="max-height: 400px">
          <div v-if="messages.length === 0" class="text-center text-gray-400 py-8">
            <div class="text-5xl mb-3">🤖</div>
            <p class="text-sm">你好！我是 AI 助手，有什么可以帮你的？</p>
            <div class="mt-4 space-y-1.5">
              <button
                v-for="tip in quickTips"
                :key="tip"
                class="block w-full text-left text-xs text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg px-3 py-2 transition-colors"
                @click="sendMessage(tip)"
              >
                💬 {{ tip }}
              </button>
            </div>
          </div>

          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="flex"
            :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div v-if="msg.role === 'assistant'" class="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-sm mr-2 flex-shrink-0 mt-1">
              🤖
            </div>
            <div
              class="max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed"
              :class="msg.role === 'user'
                ? 'bg-blue-500 text-white rounded-br-md'
                : 'bg-white border border-gray-200 text-gray-800 rounded-bl-md shadow-sm'"
              v-html="renderContent(msg.content)"
            ></div>
            <div v-if="msg.role === 'user'" class="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-sm ml-2 flex-shrink-0 mt-1">
              👤
            </div>
          </div>

          <div v-if="loading" class="flex justify-start">
            <div class="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-sm mr-2 flex-shrink-0 mt-1">
              🤖
            </div>
            <div class="bg-white border border-gray-200 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
              <div class="flex gap-1">
                <span class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
                <span class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
                <span class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="pendingConfirmation" class="px-4 py-3 bg-yellow-50 border-t border-yellow-200">
          <p class="text-sm text-yellow-800 mb-2">⚠️ {{ pendingConfirmation.detail }}</p>
          <div class="flex gap-2">
            <button
              class="flex-1 px-3 py-1.5 bg-green-500 text-white text-sm rounded-lg hover:bg-green-600 transition-colors"
              @click="confirmAction(true)"
            >
              确认
            </button>
            <button
              class="flex-1 px-3 py-1.5 bg-gray-300 text-gray-700 text-sm rounded-lg hover:bg-gray-400 transition-colors"
              @click="confirmAction(false)"
            >
              取消
            </button>
          </div>
        </div>

        <div class="px-4 py-3 bg-white border-t border-gray-200 flex items-center gap-2">
          <input
            ref="inputRef"
            v-model="input"
            class="flex-1 border border-gray-300 rounded-full px-4 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-200 transition-all"
            placeholder="输入你的问题..."
            :disabled="loading"
            @keyup.enter="sendMessage()"
          />
          <button
            class="w-9 h-9 rounded-full bg-blue-500 text-white flex items-center justify-center hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="loading || !input.trim()"
            @click="sendMessage()"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 2L11 13" />
              <path d="M22 2L15 22L11 13L2 9L22 2Z" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <button
      v-if="hasPermission && !visible"
      class="fixed bottom-6 left-[240px] z-50 w-14 h-14 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-xl hover:shadow-2xl hover:scale-110 transition-all duration-300 flex items-center justify-center group animate-pulse-subtle"
      title="AI 助手"
      @click="openChat"
    >
      <span class="text-2xl">🤖</span>
      <span class="absolute -top-1 -right-1 w-4 h-4 bg-green-400 rounded-full border-2 border-white"></span>
      <span class="absolute -bottom-8 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
        AI 助手
      </span>
    </button>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, watch } from 'vue'
import api from '../api'

const visible = ref(false)
const input = ref('')
const messages = ref([])
const loading = ref(false)
const hasPermission = ref(false)
const pendingConfirmation = ref(null)
const chatBody = ref(null)
const inputRef = ref(null)

const history = ref([])

const quickTips = [
  '查询系统状态',
  '本月薪资概况',
  '本月考勤统计',
  '查询员工数量',
]

onMounted(async () => {
  try {
    const res = await api.get('/ai/permission-status')
    hasPermission.value = res.data.has_permission
  } catch {
    hasPermission.value = false
  }
})

function openChat() {
  visible.value = true
  nextTick(() => {
    inputRef.value?.focus()
  })
}

function renderContent(text) {
  if (!text) return ''
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong class="text-blue-700">$1</strong>')
  html = html.replace(/`([^`]+)`/g, '<code class="bg-gray-100 text-pink-600 px-1 py-0.5 rounded text-xs">$1</code>')
  html = html.replace(/\n/g, '<br>')
  return html
}

async function sendMessage(msg) {
  const text = (msg || input.value).trim()
  if (!text || loading.value) return

  input.value = ''
  messages.value.push({ role: 'user', content: text })
  history.value.push({ role: 'user', content: text })

  loading.value = true
  scrollToBottom()

  try {
    const res = await api.post('/ai/chat', {
      message: text,
      history: history.value.slice(-20),
    })

    const data = res.data
    messages.value.push({ role: 'assistant', content: data.reply })
    history.value.push({ role: 'assistant', content: data.reply })

    if (data.requires_confirmation) {
      pendingConfirmation.value = {
        id: data.confirmation_id,
        detail: data.confirmation_detail,
      }
    }
  } catch {
    messages.value.push({
      role: 'assistant',
      content: '抱歉，请求失败了，请稍后重试。如果问题持续，请联系系统管理员。',
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

async function confirmAction(confirmed) {
  if (!pendingConfirmation.value) return

  try {
    const res = await api.post('/ai/confirm', {
      confirmation_id: pendingConfirmation.value.id,
      confirmed,
    })
    messages.value.push({ role: 'assistant', content: res.data.reply })
  } catch {
    messages.value.push({ role: 'assistant', content: '确认操作失败，请重试。' })
  }

  pendingConfirmation.value = null
}

function scrollToBottom() {
  nextTick(() => {
    if (chatBody.value) {
      chatBody.value.scrollTop = chatBody.value.scrollHeight
    }
  })
}

watch(visible, (val) => {
  if (val) {
    nextTick(() => scrollToBottom())
  }
})
</script>

<style scoped>
@keyframes pulse-subtle {
  0%, 100% { box-shadow: 0 8px 25px rgba(59, 130, 246, 0.3); }
  50% { box-shadow: 0 8px 35px rgba(59, 130, 246, 0.5); }
}
.animate-pulse-subtle {
  animation: pulse-subtle 3s ease-in-out infinite;
}
</style>