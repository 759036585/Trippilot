// src/views/create/types.ts
// 对话式创建行程用到的数据结构

/** 对话中逐步收集到的行程需求 */
export interface PlannerDraft {
  origin: string
  destination: string
  start_date: string
  end_date: string
  travelers: number | null
  budget: number | null
  hotel_level: string
  preferences: string[]
}

/** 还缺哪些信息：dates 同时代表出发和结束日期 */
export type MissingField =
  | 'origin'
  | 'destination'
  | 'dates'
  | 'travelers'
  | 'budget'
  | 'hotel_level'
  | 'preferences'

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  /** 网络失败时的提示气泡，不参与后续对话上下文 */
  error?: boolean
}

/** 后端 /api/v1/planner/chat 的返回 */
export interface PlannerReply {
  reply: string
  suggestions: string[]
  draft: PlannerDraft
  missing: MissingField[]
  ready: boolean
}

export const emptyDraft = (): PlannerDraft => ({
  origin: '',
  destination: '',
  start_date: '',
  end_date: '',
  travelers: null,
  budget: null,
  hotel_level: '',
  preferences: []
})
