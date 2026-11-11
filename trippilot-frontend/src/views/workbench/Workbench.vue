<!-- src/views/workbench/Workbench.vue -->
<!-- 行程工作台：这里是「胶水层」，负责数据拉取 / 轮询和模块之间的联动，
     界面拆到 components/ 下，地图、路线、周边的状态拆到 useAmap / useRoutes / useNearby -->
<template>
  <div class="workbench">
    <WorkbenchTopBar
      :ready="status === 'ready' && !!tripData"
      :origin="origin"
      :destination="tripData?.destination"
      :day-count="days.length"
      :stop-count="stopCount"
      :date-range="dateRange"
      @home="goHome"
    />

    <WorkbenchState v-if="status !== 'ready'" :status="status" @home="goHome" />

    <!-- 三栏布局 -->
    <div class="main-content" v-else>
      <!-- 左侧：每日行程列表 -->
      <ItineraryPanel
        ref="itineraryRef"
        :days="days"
        :origin="origin"
        :destination="destination"
        :transport="transport"
        :hotel="hotel"
        :stop-count="stopCount"
        :total-cost="totalCost"
        :travel-mode="travelMode"
        :travel-mode-label="travelModeLabel"
        :travel-mode-icon="travelModeIcon"
        :day-summary="daySummary"
        :routes="routes"
        :routes-loading="routesLoading"
        :active-item-id="activeItem?.id"
        :expanded-segment="expandedSegment"
        :segment-of="segmentOf"
        @select="selectItem"
        @switch-mode="switchTravelMode"
        @toggle-segment="toggleSegment"
      />

      <!-- 中间：地图 -->
      <MapPanel
        :days="days"
        :map-day="mapDay"
        :map-error="mapError"
        @select-day="handleSelectMapDay"
        @fit-all="fitAll"
        @retry="retryMap"
      />

      <!-- 右侧：预算 + 周边推荐 + AI 助手 -->
      <aside class="right-panel">
        <BudgetCard
          :breakdown="budgetBreakdown"
          :total-cost="totalCost"
          :budget="budget"
          :budget-percent="budgetPercent"
          :travelers="travelers"
        />

        <NearbyPanel
          :active-item="activeItem"
          :nearby="nearby"
          :loading="nearbyLoading"
          :category="nearbyCategory"
          :radius="nearbyRadius"
          :preview-id="previewPoiId"
          @switch-category="switchCategory"
          @switch-radius="switchRadius"
          @preview="previewPoi"
          @add="addPoi"
        />

        <AssistantCard :trip-id="tripId" />
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../../api/request'
import AssistantCard from './components/AssistantCard.vue'
import BudgetCard from './components/BudgetCard.vue'
import ItineraryPanel from './components/ItineraryPanel.vue'
import MapPanel from './components/MapPanel.vue'
import NearbyPanel from './components/NearbyPanel.vue'
import WorkbenchState from './components/WorkbenchState.vue'
import WorkbenchTopBar from './components/WorkbenchTopBar.vue'
import { fmtDate, hasCoords } from './format'
import type {
  BudgetBreakdown,
  ItemCategory,
  NearbyPoi,
  PageStatus,
  TripData,
  TripDay,
  TripHotel,
  TripItem,
  TripTransport
} from './types'
import { useAmap } from './useAmap'
import { useNearby } from './useNearby'
import { useRoutes } from './useRoutes'

const route = useRoute()
const router = useRouter()
const queryTripId = route.query.trip_id
const tripId = Array.isArray(queryTripId) ? queryTripId[0] : queryTripId

// ---------- 行程数据 ----------
const status = ref<PageStatus>('planning')
const tripData = ref<TripData | null>(null)
const activeItem = ref<TripItem | null>(null)
const activeDayIndex = ref(0)
const itineraryRef = ref<InstanceType<typeof ItineraryPanel> | null>(null)

const days = computed<TripDay[]>(() => tripData.value?.days ?? [])
const stopCount = computed(() => days.value.reduce((sum, d) => sum + d.items.length, 0))
const origin = computed(() => tripData.value?.origin || '')
const transport = computed<TripTransport | null>(() => tripData.value?.transport ?? null)
const hotel = computed<TripHotel | null>(() => tripData.value?.hotel ?? null)
const budgetBreakdown = computed<BudgetBreakdown | null>(
  () => tripData.value?.budget_breakdown ?? null
)

// 总花费包含城际交通 / 住宿 / 餐饮 / 门票玩乐等全部项目；老行程没有分类数据时退回行程项合计
const totalCost = computed(() => {
  if (budgetBreakdown.value) return Number(budgetBreakdown.value.total) || 0
  return days.value.reduce(
    (sum, d) => sum + d.items.reduce((s, i) => s + Number(i.cost_estimate || 0), 0),
    0
  )
})
const budget = computed(() => {
  const value = Number(tripData.value?.budget)
  return Number.isFinite(value) && value > 0 ? value : null
})
const budgetPercent = computed(() =>
  budget.value ? Math.min(100, Math.round((totalCost.value / budget.value) * 100)) : 0
)
const travelers = computed(() => Number(tripData.value?.travelers) || 0)
const destination = computed(() => tripData.value?.destination || '')
const dateRange = computed(() => {
  const start = days.value[0]?.date
  const end = days.value[days.value.length - 1]?.date
  if (!start || !end) return ''
  return `${fmtDate(start)} → ${fmtDate(end)}`
})

// ---------- 各功能模块 ----------
// 三个模块之间用回调互相引用，回调都在数据回来之后才执行，所以先建谁都可以
const routesApi = useRoutes({
  days,
  destination,
  onUpdated: () => amap.redrawOverlays()
})
const nearbyApi = useNearby({
  activeItem,
  onPreview: (poi) => amap.showPoiPreview(poi),
  onClearPreview: () => amap.clearPoiPreview()
})
const amap = useAmap({
  days,
  activeItem,
  hotel,
  segmentOf: routesApi.segmentOf,
  onSelectItem: selectItem
})

// 模板里要自动解包 ref，所以在这里解构成顶层绑定
const {
  routes,
  routesLoading,
  travelMode,
  expandedSegment,
  travelModeLabel,
  travelModeIcon,
  daySummary,
  segmentOf,
  loadRoutes,
  switchTravelMode,
  toggleSegment
} = routesApi

const {
  nearby,
  nearbyLoading,
  nearbyCategory,
  nearbyRadius,
  previewPoiId,
  loadNearby,
  switchCategory,
  switchRadius,
  previewPoi,
  resetPreview
} = nearbyApi

const {
  mapError,
  mapDay,
  ensureMap,
  retryMap,
  setMapDay,
  resetMapDay,
  redrawOverlays,
  highlightMarker,
  fitAll,
  locateItem,
  openInfo,
  closeInfo,
  destroy: destroyMap
} = amap

// ---------- 选中地点 ----------
function selectItem(item: TripItem, day: TripDay) {
  activeItem.value = item
  activeDayIndex.value = day.day_index
  resetPreview()

  // 折叠着的那一天先展开，再滚到这张卡片
  nextTick(() => itineraryRef.value?.revealItem(day.day_index, item.id))

  // 当前筛选把这一天隐藏了，就自动切回「全部」
  if (mapDay.value !== 0 && mapDay.value !== day.day_index) {
    resetMapDay()
  }

  highlightMarker(item.id)
  if (hasCoords(item)) {
    locateItem(item)
    openInfo(item, day)
  }

  loadNearby()
}

/** 地图上方的天筛选（0 = 全部） */
function handleSelectMapDay(index: number) {
  setMapDay(index)
  if (index === 0) return

  // 切到某一天时，如果当前选中的地点不属于这一天，就把焦点换成这天的第一个地点
  const day = days.value.find((d) => d.day_index === index)
  if (!day || !day.items.length) return
  if (day.items.some((i) => i.id === activeItem.value?.id)) return

  activeItem.value = day.items.find((i) => hasCoords(i)) ?? day.items[0]
  activeDayIndex.value = day.day_index
  closeInfo()
  resetPreview()
  nextTick(() => highlightMarker(activeItem.value?.id))
  loadNearby()
}

// ---------- 把周边推荐里的地点加入行程 ----------
// 周边推荐分类 -> 行程项类别，加入后预算能正确归到餐饮 / 购物 / 景点
const NEARBY_ITEM_CATEGORY: Record<string, ItemCategory> = {
  scenic: 'sightseeing',
  food: 'food',
  shopping: 'shopping',
  hotel: 'other'
}

async function addPoi(poi: NearbyPoi) {
  if (!tripData.value) return
  const dayIndex = activeDayIndex.value || days.value[0]?.day_index
  if (!dayIndex) return

  try {
    await request.post(`/api/v1/trips/${tripId}/days/${dayIndex}/items`, {
      place_name: poi.name,
      lng: poi.lng,
      lat: poi.lat,
      cost_estimate: 0,
      category: NEARBY_ITEM_CATEGORY[nearbyCategory.value] || 'other'
    })
    ElMessage.success(`已将「${poi.name}」加入第 ${dayIndex} 天行程`)
    await fetchTripDetail({ resetView: false })
    // 重新选中原来关注的景点
    const target = days.value
      .flatMap((d) => d.items)
      .find((i) => i.place_name === poi.name)
    if (target) {
      const day = days.value.find((d) => d.items.some((i) => i.id === target.id))
      if (day) selectItem(target, day)
    }
  } catch (error) {
    console.error('加入行程失败', error)
    ElMessage.error('加入行程失败，请稍后再试')
  }
}

// ---------- 轮询与数据 ----------
const POLL_INTERVAL = 2000
const MAX_POLL_TIMES = 150
let pollTimer: ReturnType<typeof setTimeout> | null = null
let pollCount = 0

function clearPollTimer() {
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
}

function scheduleNextPoll() {
  clearPollTimer()
  pollTimer = setTimeout(fetchTripStatus, POLL_INTERVAL)
}

function goHome() {
  clearPollTimer()
  router.push('/')
}

async function fetchTripStatus() {
  pollCount++
  try {
    const res: any = await request.get(`/api/v1/trips/${tripId}/status`)
    if (res.status === 'ready') {
      await fetchTripDetail()
    } else if (res.status === 'failed') {
      clearPollTimer()
      status.value = 'failed'
    } else if (pollCount >= MAX_POLL_TIMES) {
      clearPollTimer()
      status.value = 'failed'
    } else {
      scheduleNextPoll()
    }
  } catch (error) {
    console.error('轮询失败', error)
    if (pollCount >= MAX_POLL_TIMES) {
      clearPollTimer()
      status.value = 'failed'
    } else {
      scheduleNextPoll()
    }
  }
}

async function fetchTripDetail(options: { resetView?: boolean } = {}) {
  clearPollTimer()
  const { resetView = true } = options
  try {
    const res: any = await request.get(`/api/v1/trips/${tripId}`, { timeout: 30000 })
    const previousId = activeItem.value?.id
    tripData.value = res
    status.value = 'ready'

    await nextTick()
    const ok = await ensureMap()
    if (ok) {
      redrawOverlays()
      if (resetView) fitAll()
    }

    // 保持之前选中的地点（刷新后 id 可能变化，按名字兜底）；
    // 默认优先选第一个有坐标的景点 / 餐饮，避免一进来就选中交通站或无法定位的项目
    const allItems = days.value.flatMap((d) => d.items)
    const firstSight = allItems.find(
      (i) => hasCoords(i) && (i.category === 'sightseeing' || i.category === 'food')
    )
    const keep =
      allItems.find((i) => i.id === previousId) ??
      allItems.find((i) => i.place_name === activeItem.value?.place_name) ??
      firstSight ??
      allItems.find((i) => hasCoords(i)) ??
      allItems[0]
    if (keep) {
      const day = days.value.find((d) => d.items.some((i) => i.id === keep.id))
      if (day) {
        activeItem.value = keep
        activeDayIndex.value = day.day_index
        loadNearby()
      }
    }

    loadRoutes()
  } catch (error) {
    console.error('获取行程详情失败', error)
    status.value = 'failed'
  }
}

onMounted(() => {
  if (!tripId) {
    status.value = 'invalid'
    return
  }
  fetchTripStatus()
})

onBeforeUnmount(() => {
  clearPollTimer()
  destroyMap()
})
</script>

<style scoped>
.workbench {
  --teal: #0d9488;
  --teal-dark: #0f766e;
  --teal-soft: #ecfdf5;
  --orange: #f97316;
  --ink: #0f172a;
  --muted: #64748b;
  --line: #e8eef2;
  --bg: #f4f7f8;

  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg);
  color: var(--ink);
  font-family: 'PingFang SC', 'Microsoft YaHei', system-ui, -apple-system, sans-serif;
  -webkit-font-smoothing: antialiased;
}

/* ---------- 主体三栏 ---------- */
.main-content {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
}

/* ---------- 右栏 ---------- */
.right-panel {
  width: 342px;
  flex: 0 0 342px;
  background: #fff;
  border-left: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  overflow: hidden;
  min-height: 0;
}

/* ---------- 响应式 ---------- */
@media (max-width: 1440px) {
  .right-panel {
    width: 312px;
    flex-basis: 312px;
  }
}
@media (max-width: 1180px) {
  .right-panel {
    width: 286px;
    flex-basis: 286px;
  }
}
</style>
