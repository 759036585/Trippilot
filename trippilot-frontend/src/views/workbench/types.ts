// src/views/workbench/types.ts
// 工作台用到的所有数据结构，集中在这里，组件和 composable 共用

export type PageStatus = 'planning' | 'ready' | 'failed' | 'invalid'

export type TravelMode = 'driving' | 'transit' | 'walking'

/** 行程项类别：景点门票 / 餐饮 / 购物 / 玩乐 / 其他 */
export type ItemCategory = 'sightseeing' | 'food' | 'shopping' | 'entertainment' | 'other'

export interface TripItem {
  id: number
  place_name: string
  start_time: string
  end_time: string
  category?: ItemCategory | null
  cost_estimate: number
  note?: string | null
  lng: number | null
  lat: number | null
}

export interface TripDay {
  day_index: number
  date: string
  items: TripItem[]
}

/** 城际交通的一种方案（推荐或备选） */
export interface TransportOption {
  mode: string
  summary: string
  departure_time?: string
  arrival_time?: string
  duration_minutes?: number
  cost?: number
  note?: string
}

export interface TripTransport {
  recommended: TransportOption
  alternatives?: TransportOption[]
}

/** 住宿方案 */
export interface TripHotel {
  name: string
  address?: string
  lng?: number | null
  lat?: number | null
  rating?: string
  check_in_date?: string
  check_out_date?: string
  nights?: number
  rooms?: number
  price_per_night?: number
  cost?: number
  note?: string
}

/** 分类预算（元） */
export interface BudgetBreakdown {
  transport: number
  local_transport: number
  accommodation: number
  food: number
  tickets: number
  shopping: number
  other: number
  total: number
}

export interface TripData {
  trip_id: number
  origin?: string | null
  destination: string
  status: string
  start_date?: string
  end_date?: string
  budget?: number | null
  travelers?: number | null
  transport?: TripTransport | null
  hotel?: TripHotel | null
  budget_breakdown?: BudgetBreakdown | null
  total_cost?: number
  days: TripDay[]
}

export interface RouteStep {
  mode: 'drive' | 'walk' | 'bus' | 'subway'
  text?: string
  line?: string
  direction?: string
  from?: string
  to?: string
  stops?: number
  distance?: number
  duration?: number
}

export interface RouteInfo {
  distance: number
  duration: number
  points: [number, number][]
  estimated?: boolean
  mode?: string
  /** 打车预估车费 / 公交票价（元） */
  cost?: number | null
  steps?: RouteStep[]
}

export interface NearbyPoi {
  id: string
  name: string
  address: string
  distance: number
  type: string
  rating: string
  tel: string
  photo: string
  lng: number
  lat: number
}

/** 某一天所有路段的汇总 */
export interface DayRouteSummary {
  distance: number
  duration: number
}
