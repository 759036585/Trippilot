// src/views/workbench/constants.ts
// 工作台里固定的选项 / 颜色，UI 和逻辑都用这一份
import type { ItemCategory, TravelMode } from './types'

/** 每天的主题色，按 day_index 循环取用 */
export const DAY_COLORS = ['#0ea5e9', '#f97316', '#8b5cf6', '#10b981', '#ef4444', '#f59e0b', '#06b6d4']

/** 出行方式切换栏的选项 */
export const TRAVEL_MODES: ReadonlyArray<{
  key: TravelMode
  label: string
  icon: string
  desc: string
}> = [
  { key: 'driving', label: '打车', icon: '🚕', desc: '按驾车路线估算耗时和车费' },
  { key: 'transit', label: '公交', icon: '🚇', desc: '公交 / 地铁换乘方案，可看具体怎么坐' },
  { key: 'walking', label: '步行', icon: '🚶', desc: '步行路线与耗时' }
]

/** 周边推荐的分类 */
export const NEARBY_CATEGORIES = [
  { key: 'scenic', label: '景点' },
  { key: 'food', label: '美食' },
  { key: 'hotel', label: '住宿' },
  { key: 'shopping', label: '购物' }
]

/** 周边推荐的可选半径（米） */
export const NEARBY_RADII = [1000, 2000, 5000]

/** 没配图时每个分类用的占位图标 */
export const CATEGORY_ICONS: Record<string, string> = {
  scenic: '🏞',
  food: '🍜',
  hotel: '🏨',
  shopping: '🛍'
}

/** 记住用户上次选的出行方式 */
export const TRAVEL_MODE_STORAGE_KEY = 'tp_travel_mode'

/** 行程项类别：图标 / 名称 / 主题色 */
export const ITEM_CATEGORIES: Record<
  ItemCategory,
  { label: string; icon: string; color: string }
> = {
  sightseeing: { label: '景点', icon: '🎫', color: '#0d9488' },
  food: { label: '餐饮', icon: '🍜', color: '#f97316' },
  shopping: { label: '购物', icon: '🛍', color: '#8b5cf6' },
  entertainment: { label: '玩乐', icon: '🎡', color: '#ec4899' },
  other: { label: '其他', icon: '📍', color: '#64748b' }
}

/** 城际交通方式：图标 / 名称 */
export const TRANSPORT_MODE_META: Record<string, { label: string; icon: string }> = {
  high_speed_rail: { label: '高铁', icon: '🚄' },
  train: { label: '火车', icon: '🚆' },
  flight: { label: '飞机', icon: '✈️' },
  bus: { label: '大巴', icon: '🚌' },
  driving: { label: '自驾', icon: '🚗' },
  other: { label: '交通', icon: '🧭' }
}

/** 城际交通没填时长 / 费用时展示的占位 */
export const TRANSPORT_MODE_FALLBACK = TRANSPORT_MODE_META.other
