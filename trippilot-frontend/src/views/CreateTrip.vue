<!-- src/views/CreateTrip.vue -->
<!-- 对话式创建行程：AI 像旅行顾问一样一步步问清需求，右侧实时汇总 -->
<template>
  <div class="create-page">
    <AppHeader solid />

    <main class="planner-main">
      <!-- 左：对话区 -->
      <section class="chat-shell">
        <header class="chat-head">
          <span class="chat-logo">✈</span>
          <div class="chat-title">
            <h1>行程助手</h1>
            <p><span class="online-dot"></span>在线 · 一步一步帮你规划</p>
          </div>
          <span class="chat-count">{{ filledCount }}/6</span>
          <button type="button" class="reset-btn" :disabled="loading" @click="resetChat">
            <el-icon><RefreshLeft /></el-icon>
            重新开始
          </button>
        </header>

        <!-- 游客提示 -->
        <div v-if="!userStore.isLoggedIn" class="guest-bar">
          <el-icon><InfoFilled /></el-icon>
          <span>当前为游客模式，生成的行程不会保存</span>
          <button type="button" @click="goLogin">登录后自动保存 →</button>
        </div>

        <div ref="scrollRef" class="chat-scroll">
          <!-- 对话气泡 -->
          <div
            v-for="message in messages"
            :key="message.id"
            class="msg"
            :class="message.role === 'user' ? 'msg--user' : 'msg--ai'"
          >
            <span v-if="message.role === 'assistant'" class="msg-avatar">AI</span>
            <div class="bubble" :class="{ 'bubble--error': message.error }">
              {{ message.content }}
            </div>
          </div>

          <!-- 正在思考 -->
          <div v-if="loading" class="msg msg--ai">
            <span class="msg-avatar">AI</span>
            <div class="bubble typing" aria-label="助手正在输入">
              <i></i><i></i><i></i>
            </div>
          </div>

          <!-- 需求齐全后的确认卡片 -->
          <DraftSummary
            v-if="ready && !loading"
            :draft="draft"
            :submitting="submitting"
            @confirm="confirmPlan"
          />

          <!-- 快捷选项 -->
          <div v-if="showSuggestions" class="chips">
            <button
              v-for="suggestion in suggestions"
              :key="suggestion"
              type="button"
              @click="sendSuggestion(suggestion)"
            >
              {{ suggestion }}
            </button>
          </div>

          <!-- 请求失败后的重试 -->
          <div v-if="lastMessageFailed" class="retry-row">
            <button type="button" @click="retry">重新连接</button>
          </div>
        </div>

        <!-- 输入区 -->
        <footer class="composer">
          <el-input
            v-model="input"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 4 }"
            resize="none"
            placeholder="说说你的出行想法，比如「下周末去成都玩三天」"
            @keydown="onKeydown"
          />
          <button type="button" class="send-btn" :disabled="!canSend" @click="sendInput">
            <el-icon><Promotion /></el-icon>
          </button>
        </footer>
      </section>

      <!-- 右：已收集的需求 -->
      <aside class="side-col">
        <PlannerProgress
          :draft="draft"
          :missing="missing"
          :ready="ready"
          :submitting="submitting"
          @confirm="confirmPlan"
        />

        <section class="tips-card">
          <h4>你可以这样说</h4>
          <ul>
            <li>「从北京去大理，下周三出发，玩 4 天」</li>
            <li>「两个人，预算 8000，想住舒适型」</li>
            <li>「喜欢美食和自然风景，节奏慢一点」</li>
          </ul>
        </section>
      </aside>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { InfoFilled, Promotion, RefreshLeft } from '@element-plus/icons-vue'
import request, { errorMessage } from '../api/request'
import AppHeader from '../components/AppHeader.vue'
import { useUserStore } from '../stores/user'
import DraftSummary from './create/DraftSummary.vue'
import PlannerProgress from './create/PlannerProgress.vue'
import { usePlannerChat } from './create/usePlannerChat'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const {
  messages,
  draft,
  suggestions,
  missing,
  ready,
  loading,
  start,
  send,
  retry,
  reset,
  pushAssistant,
  pushUser
} = usePlannerChat()

const input = ref('')
const submitting = ref(false)
const submitted = ref(false)
const scrollRef = ref<HTMLElement | null>(null)

const filledCount = computed(() => 6 - missing.value.length)
const canSend = computed(() => Boolean(input.value.trim()) && !loading.value && !submitting.value)
const lastMessageFailed = computed(() => {
  const last = messages.value[messages.value.length - 1]
  return Boolean(last?.error)
})
const showSuggestions = computed(
  () => !loading.value && !submitting.value && suggestions.value.length > 0 && !lastMessageFailed.value
)

// 新消息 / 思考中 / 需求齐全时都滚到底部
function scrollToBottom() {
  nextTick(() => {
    const el = scrollRef.value
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  })
}
watch([() => messages.value.length, loading, ready], scrollToBottom)

onMounted(async () => {
  const queryDestination = typeof route.query.destination === 'string' ? route.query.destination.trim() : ''
  await start(queryDestination)
  scrollToBottom()
})

function onKeydown(event: Event) {
  const keyboardEvent = event as KeyboardEvent
  // 输入法选词时的回车不能当成发送
  if (keyboardEvent.key === 'Enter' && !keyboardEvent.shiftKey && !keyboardEvent.isComposing) {
    keyboardEvent.preventDefault()
    void sendInput()
  }
}

// 需求齐了以后，用户点「可以，开始生成」或直接打字确认，都直接提交，不再绕一圈模型。
// 同时出现修改意图（改预算 / 加偏好等）时，仍然交给助手处理。
const CONFIRM_WORDS = /(开始生成|开始吧|就按这个|就这样|就这些|确认|没问题|可以|好的)/
const MODIFIER_WORDS = /(改|换|加|减|不要|别|预算|酒店|住宿|天|人|元|景点|美食|风景)/

function isConfirmPhrase(text: string) {
  const content = text.trim()
  return content.length <= 16 && CONFIRM_WORDS.test(content) && !MODIFIER_WORDS.test(content)
}

async function sendInput() {
  const text = input.value.trim()
  if (!text || loading.value || submitting.value) return
  input.value = ''
  if (ready.value && isConfirmPhrase(text)) {
    await confirmPlan(text)
    return
  }
  await send(text)
}

async function sendSuggestion(text: string) {
  if (loading.value || submitting.value) return
  if (ready.value && isConfirmPhrase(text)) {
    await confirmPlan(text)
    return
  }
  await send(text)
}

async function resetChat() {
  if (loading.value) return
  input.value = ''
  submitted.value = false
  reset()
}

function goLogin() {
  router.push({ path: '/login', query: { redirect: route.fullPath } })
}

/** 需求确认后：沿用原来的创建接口，提交完直接进工作台看规划进度 */
async function confirmPlan(fromText?: string) {
  if (!ready.value || submitting.value || submitted.value || loading.value) return
  if (!draft.value.start_date || !draft.value.end_date) {
    ElMessage.warning('日期还没确定，先告诉助手什么时候出发吧')
    return
  }

  submitting.value = true
  if (fromText) pushUser(fromText)
  try {
    const res = (await request.post(
      '/api/v1/trips',
      {
        origin: draft.value.origin,
        destination: draft.value.destination,
        start_date: draft.value.start_date,
        end_date: draft.value.end_date,
        travelers: draft.value.travelers ?? 2,
        budget: draft.value.budget ?? 5000,
        preferences: draft.value.preferences,
        hotel_level: draft.value.hotel_level || '舒适型'
      },
      { timeout: 30000 }
    )) as unknown as { trip_id: number }

    submitted.value = true
    pushAssistant('好嘞，需求收到！正在查真实景点、算交通和预算，马上带你去工作台看结果 🚀')
    ElMessage.success('已提交，AI 开始规划行程')
    window.setTimeout(() => {
      router.push({ path: '/workbench', query: { trip_id: res.trip_id } })
    }, 700)
  } catch (error) {
    ElMessage.error(errorMessage(error, '提交失败，请稍后再试'))
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.create-page {
  min-height: 100vh;
  background:
    radial-gradient(900px 420px at 12% -8%, rgba(20, 184, 166, 0.1), transparent 70%),
    radial-gradient(760px 380px at 92% 0%, rgba(99, 102, 241, 0.08), transparent 70%),
    #f6f8fb;
}

.planner-main {
  max-width: 1180px;
  margin: 0 auto;
  padding: 24px 24px 28px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 308px;
  gap: 20px;
  height: calc(100vh - 64px);
  min-height: 560px;
}

/* ---------------- 对话区 ---------------- */
.chat-shell {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 20px;
  box-shadow: 0 20px 44px rgba(15, 23, 42, 0.07);
  overflow: hidden;
}

.chat-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid #f1f5f9;
  background: rgba(255, 255, 255, 0.9);
}
.chat-logo {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: linear-gradient(135deg, #14b8a6, #0d9488);
  color: #fff;
  font-size: 17px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 18px rgba(13, 148, 136, 0.26);
  flex: 0 0 auto;
}
.chat-title {
  min-width: 0;
}
.chat-title h1 {
  margin: 0;
  font-size: 16px;
  color: #0f172a;
  letter-spacing: 0.3px;
}
.chat-title p {
  margin: 3px 0 0;
  font-size: 11.5px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 5px;
}
.online-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.14);
}
.chat-count {
  margin-left: auto;
  font-size: 12px;
  font-weight: 700;
  color: #0d9488;
  background: #e6fffb;
  border-radius: 999px;
  padding: 4px 10px;
}
.reset-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid #eef2f7;
  background: #fff;
  color: #64748b;
  border-radius: 9px;
  padding: 6px 10px;
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  transition: color 0.2s ease, border-color 0.2s ease;
}
.reset-btn:hover:not(:disabled) {
  color: #0d9488;
  border-color: #ccfbf1;
}
.reset-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.guest-bar {
  display: flex;
  align-items: center;
  gap: 7px;
  flex-wrap: wrap;
  padding: 9px 20px;
  font-size: 12px;
  color: #92400e;
  background: #fffbeb;
  border-bottom: 1px solid #fef3c7;
}
.guest-bar .el-icon {
  color: #d97706;
}
.guest-bar button {
  margin-left: auto;
  border: none;
  background: none;
  padding: 0;
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  color: #0d9488;
  cursor: pointer;
}

.chat-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 22px 22px 10px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  scrollbar-width: thin;
}
.chat-scroll::-webkit-scrollbar {
  width: 6px;
}
.chat-scroll::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 999px;
}

.msg {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  max-width: 100%;
}
.msg--user {
  justify-content: flex-end;
}
.msg-avatar {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  font-size: 10.5px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  box-shadow: 0 6px 14px rgba(99, 102, 241, 0.24);
}
.bubble {
  max-width: min(78%, 520px);
  padding: 11px 14px;
  border-radius: 4px 14px 14px 14px;
  background: #f8fafc;
  border: 1px solid #eef2f7;
  color: #334155;
  font-size: 13.5px;
  line-height: 1.75;
  white-space: pre-wrap;
  word-break: break-word;
  animation: bubble-in 0.22s ease;
}
.msg--user .bubble {
  border-radius: 14px 4px 14px 14px;
  background: linear-gradient(135deg, #14b8a6, #0d9488);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 10px 22px rgba(13, 148, 136, 0.2);
}
.bubble--error {
  background: #fef2f2;
  border-color: #fecaca;
  color: #b91c1c;
}

@keyframes bubble-in {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 打字中 */
.typing {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 15px 16px;
}
.typing i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #94a3b8;
  animation: typing-bounce 1.1s infinite ease-in-out;
}
.typing i:nth-child(2) {
  animation-delay: 0.15s;
}
.typing i:nth-child(3) {
  animation-delay: 0.3s;
}
@keyframes typing-bounce {
  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.5;
  }
  30% {
    transform: translateY(-4px);
    opacity: 1;
  }
}

/* 快捷选项 */
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding-left: 39px;
}
.chips button {
  border: 1px solid #ccfbf1;
  background: #f0fdfa;
  color: #0f766e;
  border-radius: 999px;
  padding: 7px 13px;
  font-size: 12.5px;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}
.chips button:hover {
  background: #ccfbf1;
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(13, 148, 136, 0.12);
}

.retry-row {
  padding-left: 39px;
}
.retry-row button {
  border: 1px solid #fecaca;
  background: #fff;
  color: #b91c1c;
  border-radius: 999px;
  padding: 6px 14px;
  font-size: 12.5px;
  font-family: inherit;
  cursor: pointer;
}

/* 输入区 */
.composer {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 12px 16px 14px;
  border-top: 1px solid #f1f5f9;
  background: #fff;
}
.composer :deep(.el-textarea__inner) {
  border-radius: 12px;
  border: 1px solid #eef2f7;
  background: #f8fafc;
  box-shadow: none;
  font-family: inherit;
  font-size: 13.5px;
  line-height: 1.6;
  padding: 10px 13px;
  color: #0f172a;
  transition: border-color 0.2s ease, background 0.2s ease;
}
.composer :deep(.el-textarea__inner:focus) {
  border-color: #99f6e4;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.1);
}
.send-btn {
  width: 40px;
  height: 40px;
  flex: 0 0 auto;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #14b8a6, #0d9488);
  color: #fff;
  font-size: 17px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 10px 22px rgba(13, 148, 136, 0.24);
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}
.send-btn:disabled {
  opacity: 0.4;
  cursor: default;
  box-shadow: none;
}

/* ---------------- 右栏 ---------------- */
.side-col {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: thin;
}

.tips-card {
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 16px;
  padding: 16px 18px;
}
.tips-card h4 {
  margin: 0 0 10px;
  font-size: 13px;
  color: #0f172a;
}
.tips-card ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.tips-card li {
  font-size: 12px;
  line-height: 1.6;
  color: #64748b;
  background: #f8fafc;
  border-radius: 9px;
  padding: 8px 10px;
}

/* ---------------- 响应式 ---------------- */
@media (max-width: 980px) {
  .planner-main {
    grid-template-columns: minmax(0, 1fr);
    height: auto;
    min-height: 0;
    padding: 14px;
  }
  .side-col {
    display: none;
  }
  .chat-shell {
    height: calc(100vh - 92px);
    min-height: 520px;
  }
  .chat-scroll {
    padding: 16px 14px 8px;
  }
  .chips {
    padding-left: 0;
  }
  .retry-row {
    padding-left: 0;
  }
  .bubble {
    max-width: 84%;
  }
  .reset-btn {
    font-size: 0;
    gap: 0;
    padding: 7px 9px;
  }
  .reset-btn .el-icon {
    font-size: 14px;
  }
}

@media (max-width: 560px) {
  .guest-bar span {
    flex: 1 1 100%;
    order: 2;
  }
  .guest-bar button {
    margin-left: 0;
    order: 1;
  }
  .chat-title p {
    font-size: 11px;
  }
}
</style>
