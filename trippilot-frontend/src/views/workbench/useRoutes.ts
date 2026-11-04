// src/views/workbench/useRoutes.ts
// 出行方式 + 路段规划：向 /api/v1/routes 批量算路线，提供每段的展示数据和兜底估算
import { computed, ref, type Ref } from 'vue'
import request from '../../api/request'
import { TRAVEL_MODES, TRAVEL_MODE_STORAGE_KEY } from './constants'
import { hasCoords, haversine, segmentKey } from './format'
import type { DayRouteSummary, RouteInfo, RouteStep, TravelMode, TripDay } from './types'

interface UseRoutesOptions {
  days: Ref<TripDay[]>
  destination: Ref<string>
  /** 路线数据更新后（需要重画地图）时回调 */
  onUpdated?: () => void
}

export function useRoutes(options: UseRoutesOptions) {
  const routes = ref<Record<string, RouteInfo>>({})
  const routesLoading = ref(false)
  let requestSeq = 0

  const travelMode = ref<TravelMode>(readStoredTravelMode())
  const expandedSegment = ref('')

  const travelModeLabel = computed(
    () => TRAVEL_MODES.find((m) => m.key === travelMode.value)?.label ?? '打车'
  )
  const travelModeIcon = computed(
    () => TRAVEL_MODES.find((m) => m.key === travelMode.value)?.icon ?? '🚕'
  )

  function readStoredTravelMode(): TravelMode {
    const stored = localStorage.getItem(TRAVEL_MODE_STORAGE_KEY)
    return stored === 'transit' || stored === 'walking' ? stored : 'driving'
  }

  function segSteps(dayIndex: number, index: number): RouteStep[] {
    return routes.value[segmentKey(dayIndex, index)]?.steps ?? []
  }

  function toggleSegment(dayIndex: number, index: number) {
    if (!segSteps(dayIndex, index).length) return
    const key = segmentKey(dayIndex, index)
    expandedSegment.value = expandedSegment.value === key ? '' : key
  }

  async function loadRoutes() {
    const segs: { key: string; origin: string; destination: string }[] = []
    options.days.value.forEach((day) => {
      const items = day.items
      for (let i = 0; i < items.length - 1; i++) {
        const from = items[i]
        const to = items[i + 1]
        if (!hasCoords(from) || !hasCoords(to)) continue
        segs.push({
          key: segmentKey(day.day_index, i),
          origin: `${from.lng},${from.lat}`,
          destination: `${to.lng},${to.lat}`
        })
      }
    })

    const seq = ++requestSeq
    if (!segs.length) {
      routes.value = {}
      return
    }

    routesLoading.value = true
    try {
      const res: any = await request.post('/api/v1/routes', {
        // 公交规划需要城市，直接用行程目的地
        city: options.destination.value || '',
        segments: segs.map((s) => ({
          origin: s.origin,
          destination: s.destination,
          mode: travelMode.value
        }))
      })
      if (seq !== requestSeq) return
      const next: Record<string, RouteInfo> = {}
      segs.forEach((seg, i) => {
        const data = res?.routes?.[i]
        if (data) next[seg.key] = data
      })
      routes.value = next
      options.onUpdated?.()
    } catch (error) {
      console.warn('路线计算失败，改为直线连接', error)
    } finally {
      if (seq === requestSeq) routesLoading.value = false
    }
  }

  async function switchTravelMode(mode: TravelMode) {
    if (travelMode.value === mode) return
    travelMode.value = mode
    // 记住上次选的出行方式，下次打开工作台不用再切
    localStorage.setItem(TRAVEL_MODE_STORAGE_KEY, mode)
    expandedSegment.value = ''
    routes.value = {}
    await loadRoutes()
  }

  /**
   * 取某一段的展示数据：优先用高德返回的真实路线，
   * 查不到时（限流 / 两点过近）按直线距离估算兜底；公交不估算。
   */
  function segmentOf(dayIndex: number, index: number): RouteInfo | undefined {
    const real = routes.value[segmentKey(dayIndex, index)]
    if (real && real.distance > 0) return real

    // 公交没有可用的直线估算，宁愿显示「暂无方案」也不给假数据
    if (travelMode.value === 'transit') return undefined

    const day = options.days.value.find((d) => d.day_index === dayIndex)
    const from = day?.items[index]
    const to = day?.items[index + 1]
    if (!hasCoords(from) || !hasCoords(to)) return undefined

    const distance = haversine(
      from!.lng as number,
      from!.lat as number,
      to!.lng as number,
      to!.lat as number
    )
    // 步行按 4.7km/h；打车近距离起步慢，按 10km/h，远距离按 27km/h
    const speed = travelMode.value === 'walking' ? 1.3 : distance < 1200 ? 2.8 : 7.5
    return {
      distance: Math.round(distance),
      duration: Math.round(distance / speed),
      points: [],
      estimated: true,
      mode: travelMode.value
    }
  }

  /** 每天已算出路线的距离 / 时长合计 */
  const daySummary = computed<Record<number, DayRouteSummary>>(() => {
    const summary: Record<number, DayRouteSummary> = {}
    options.days.value.forEach((day) => {
      let distance = 0
      let duration = 0
      let found = false
      day.items.forEach((_, index) => {
        const seg = segmentOf(day.day_index, index)
        if (seg) {
          distance += seg.distance
          duration += seg.duration
          found = true
        }
      })
      if (found) summary[day.day_index] = { distance, duration }
    })
    return summary
  })

  return {
    routes,
    routesLoading,
    travelMode,
    expandedSegment,
    travelModeLabel,
    travelModeIcon,
    loadRoutes,
    switchTravelMode,
    segmentOf,
    segSteps,
    toggleSegment,
    daySummary
  }
}
