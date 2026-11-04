// src/views/workbench/constants.ts
// 工作台里固定的选项 / 颜色，UI 和逻辑都用这一份
import type { TravelMode } from './types'

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
