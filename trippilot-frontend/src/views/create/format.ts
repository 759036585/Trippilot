// src/views/create/format.ts
// 对话界面的日期 / 金额格式化工具

const WEEK = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

/** 2026-11-20 → 11月20日 */
export function fmtMonthDay(iso: string): string {
  const date = new Date(`${iso}T00:00:00`)
  if (Number.isNaN(date.getTime())) return iso
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

/** 2026-11-20 → 11月20日 周五 */
export function fmtDateWithWeek(iso: string): string {
  const date = new Date(`${iso}T00:00:00`)
  if (Number.isNaN(date.getTime())) return iso
  return `${fmtMonthDay(iso)} ${WEEK[date.getDay()]}`
}

/** 行程天数（含首尾），日期缺失时返回 0 */
export function tripDayCount(start: string, end: string): number {
  if (!start || !end) return 0
  const from = new Date(`${start}T00:00:00`).getTime()
  const to = new Date(`${end}T00:00:00`).getTime()
  if (Number.isNaN(from) || Number.isNaN(to) || to < from) return 0
  return Math.round((to - from) / 86400000) + 1
}

/** 5000 → ¥5,000 */
export function fmtMoney(value: number | null | undefined): string {
  if (!value) return ''
  return `¥${Math.round(value).toLocaleString('zh-CN')}`
}
