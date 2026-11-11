// src/views/workbench/format.ts
// 纯函数工具：日期 / 金额 / 距离 / 时长格式化，以及坐标相关的小判断
import { DAY_COLORS, ITEM_CATEGORIES, TRANSPORT_MODE_META, TRANSPORT_MODE_FALLBACK } from './constants'
import type { ItemCategory, TripDay, TripItem } from './types'

/** 按天取主题色（支持任意整数下标） */
export function dayColor(index: number) {
  return DAY_COLORS[((index % DAY_COLORS.length) + DAY_COLORS.length) % DAY_COLORS.length]
}

/** 行程项类别的展示信息，未知类别按「其他」处理 */
export function catMeta(category?: string | null) {
  const key = (category || 'sightseeing') as ItemCategory
  return ITEM_CATEGORIES[key] ?? ITEM_CATEGORIES.other
}

/** 城际交通方式的展示信息 */
export function transportMeta(mode?: string | null) {
  return TRANSPORT_MODE_META[mode || ''] ?? TRANSPORT_MODE_FALLBACK
}

/** 把「分钟」格式化成「4 小时 24 分」 */
export function fmtMinutes(minutes?: number | null) {
  const total = Math.round(Number(minutes) || 0)
  if (total <= 0) return '—'
  if (total < 60) return `${total} 分钟`
  const h = Math.floor(total / 60)
  const m = total % 60
  return m ? `${h} 小时 ${m} 分` : `${h} 小时`
}

export function fmtMoney(value: number | string | null | undefined) {
  const num = Number(value || 0)
  return num >= 1000 ? num.toLocaleString('zh-CN', { maximumFractionDigits: 0 }) : `${Math.round(num)}`
}

export function fmtDist(meters: number) {
  if (!meters || meters <= 0) return '—'
  return meters >= 1000 ? `${(meters / 1000).toFixed(1)} km` : `${Math.round(meters)} m`
}

export function fmtDur(seconds: number) {
  if (!seconds || seconds <= 0) return '—'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} 分钟`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m ? `${h} 小时 ${m} 分` : `${h} 小时`
}

export function parseDate(dateStr?: string) {
  const [y, m, d] = (dateStr || '').split('-').map(Number)
  if (!y || !m || !d) return null
  return new Date(y, m - 1, d)
}

export function fmtDate(dateStr?: string) {
  const date = parseDate(dateStr)
  if (!date) return dateStr || ''
  return `${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

export function weekday(dateStr?: string) {
  const date = parseDate(dateStr)
  if (!date) return ''
  return ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][date.getDay()]
}

/** 拼到 innerHTML 里的内容必须先转义 */
export function esc(text: string) {
  return String(text ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] as string)
  )
}

export function hasCoords(item?: TripItem | null): boolean {
  return !!item && item.lng != null && item.lat != null
}

/** 一天的门票 / 活动花费合计 */
export function dayCost(day: TripDay) {
  return day.items.reduce((sum, item) => sum + Number(item.cost_estimate || 0), 0)
}

/** 两点的球面直线距离（米），高德没返回路线时用来估算 */
export function haversine(lng1: number, lat1: number, lng2: number, lat2: number) {
  const R = 6371000
  const toRad = (deg: number) => (deg * Math.PI) / 180
  const dLat = toRad(lat2 - lat1)
  const dLng = toRad(lng2 - lng1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(a))
}

/** 路段 key：第几天 + 第几段，routes 字典和展开状态都用它 */
export function segmentKey(dayIndex: number, index: number) {
  return `${dayIndex}-${index}`
}
