// src/views/workbench/types.ts
// 工作台用到的所有数据结构，集中在这里，组件和 composable 共用

export type PageStatus = 'planning' | 'ready' | 'failed' | 'invalid'

export type TravelMode = 'driving' | 'transit' | 'walking'

export interface TripItem {
  id: number
  place_name: string
  start_time: string
  end_time: string
  cost_estimate: number
  lng: number | null
  lat: number | null
}

export interface TripDay {
  day_index: number
  date: string
  items: TripItem[]
}

export interface TripData {
  trip_id: number
  destination: string
  status: string
  start_date?: string
  end_date?: string
  budget?: number | null
  travelers?: number | null
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
