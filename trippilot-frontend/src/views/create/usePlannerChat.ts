// src/views/create/usePlannerChat.ts
// 对话式创建行程的状态机：维护消息列表、已收集需求、待补字段和请求状态
import { ref } from 'vue'
import request, { errorMessage } from '../../api/request'
import { emptyDraft } from './types'
import type { ChatMessage, MissingField, PlannerDraft, PlannerReply } from './types'

// 一轮对话要等模型抽取信息，比普通接口慢，单独放宽超时
const CHAT_TIMEOUT = 60000

export function usePlannerChat() {
  const messages = ref<ChatMessage[]>([])
  const draft = ref<PlannerDraft>(emptyDraft())
  const suggestions = ref<string[]>([])
  const missing = ref<MissingField[]>([
    'origin',
    'destination',
    'dates',
    'travelers',
    'budget',
    'hotel_level'
  ])
  const ready = ref(false)
  const loading = ref(false)

  let seq = 0
  let started = false

  function pushAssistant(content: string, error = false) {
    messages.value.push({ id: ++seq, role: 'assistant', content, error })
  }

  function pushUser(content: string) {
    messages.value.push({ id: ++seq, role: 'user', content })
  }

  function apply(reply: PlannerReply) {
    if (reply.reply) pushAssistant(reply.reply)
    draft.value = reply.draft ?? emptyDraft()
    suggestions.value = Array.isArray(reply.suggestions) ? reply.suggestions : []
    missing.value = Array.isArray(reply.missing) ? reply.missing : []
    ready.value = Boolean(reply.ready)
  }

  async function requestTurn() {
    loading.value = true
    try {
      // 错误提示气泡只是给用户看的，不作为对话上下文发给模型
      const history = messages.value
        .filter((message) => !message.error)
        .map(({ role, content }) => ({ role, content }))

      const reply = (await request.post(
        '/api/v1/planner/chat',
        { messages: history, draft: draft.value },
        { timeout: CHAT_TIMEOUT }
      )) as unknown as PlannerReply

      apply(reply)
    } catch (error) {
      pushAssistant(errorMessage(error, '连接助手失败了，点「重试」再试一次'), true)
      suggestions.value = []
    } finally {
      loading.value = false
    }
  }

  /** 发送一句话：先上屏用户气泡，再等助手回复 */
  async function send(text: string) {
    const content = text.trim()
    if (!content || loading.value) return
    pushUser(content)
    suggestions.value = []
    await requestTurn()
  }

  /** 页面进入时启动对话；带目的地时直接当作第一句用户需求 */
  async function start(destination = '') {
    if (started) return
    started = true
    if (destination) {
      await send(`我想去${destination}玩`)
    } else {
      // messages 为空时后端直接返回开场白，不调用模型
      await requestTurn()
    }
  }

  /** 上一次请求失败后重试，复用已有的对话历史 */
  async function retry() {
    if (loading.value) return
    if (messages.value[messages.value.length - 1]?.error) {
      messages.value.pop()
    }
    await requestTurn()
  }

  /** 重新开始：清空对话和已收集需求 */
  function reset() {
    messages.value = []
    draft.value = emptyDraft()
    suggestions.value = []
    missing.value = [
      'origin',
      'destination',
      'dates',
      'travelers',
      'budget',
      'hotel_level'
    ]
    ready.value = false
    seq = 0
    started = true
    void requestTurn()
  }

  return {
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
  }
}
