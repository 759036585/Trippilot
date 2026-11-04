<!-- src/views/Workbench.vue -->
<template>
  <div class="workbench">
    <!-- 顶部栏 -->
    <header class="top-bar">
      <div class="brand">
        <div class="brand-mark">✈</div>
        <div class="brand-text">
          <span class="brand-name">旅程 AI</span>
          <span class="brand-sub">行程工作台</span>
        </div>
      </div>

      <div class="trip-meta" v-if="tripData && status === 'ready'">
        <span class="pill pill--dest">{{ tripData.destination }}</span>
        <span class="pill">{{ days.length }} 天 · {{ stopCount }} 个地点</span>
        <span class="pill" v-if="dateRange">{{ dateRange }}</span>
        <span class="badge-done">已生成</span>
      </div>

      <button class="ghost-btn" @click="goHome">
        <el-icon><RefreshRight /></el-icon>
        重新规划
      </button>
    </header>

    <!-- 加载状态 -->
    <div v-if="status === 'planning'" class="state-page">
      <div class="planning-card">
        <div class="orbit">
          <span class="orbit-ring"></span>
          <span class="orbit-plane">✈</span>
        </div>
        <h3>AI 正在为你精心规划行程</h3>
        <p>正在查询真实景点、计算交通耗时并安排每日路线，请稍候…</p>
        <div class="skeleton-lines">
          <i style="width: 78%"></i>
          <i style="width: 60%"></i>
          <i style="width: 68%"></i>
        </div>
      </div>
    </div>

    <!-- 失败状态 -->
    <div v-else-if="status === 'failed'" class="state-page">
      <el-result icon="error" title="规划失败" sub-title="AI 规划行程时出错了，请返回重新提交一次。">
        <template #extra>
          <el-button type="primary" @click="goHome">返回重新规划</el-button>
        </template>
      </el-result>
    </div>

    <!-- 缺少 trip_id -->
    <div v-else-if="status === 'invalid'" class="state-page">
      <el-result icon="warning" title="缺少行程参数" sub-title="地址中没有 trip_id，请重新提交规划需求。">
        <template #extra>
          <el-button type="primary" @click="goHome">返回重新规划</el-button>
        </template>
      </el-result>
    </div>

    <!-- 三栏布局 -->
    <div class="main-content" v-else>
      <!-- 左侧：每日行程列表 -->
      <aside class="left-panel">
        <div class="panel-head">
          <div>
            <h3>行程安排</h3>
            <p class="panel-sub">{{ days.length }} 天 · {{ stopCount }} 个地点 · 预计 ¥{{ fmtMoney(totalCost) }}</p>
          </div>
          <button class="mini-btn" v-if="hasCollapsed" @click="expandAll">展开全部</button>
        </div>

        <!-- 出行方式切换 -->
        <div class="mode-bar">
          <button
            v-for="option in travelModes"
            :key="option.key"
            class="mode-btn"
            :class="{ on: travelMode === option.key }"
            :title="option.desc"
            @click="switchTravelMode(option.key)"
          >
            <span class="mode-btn__icon">{{ option.icon }}</span>
            {{ option.label }}
          </button>
        </div>

        <div class="panel-scroll">
          <section
            v-for="day in days"
            :key="day.day_index"
            class="day-section"
            :class="{ collapsed: isCollapsed(day.day_index) }"
          >
            <button class="day-head" @click="toggleDay(day.day_index)">
              <span class="day-badge" :style="{ background: dayColor(day.day_index - 1) }">
                {{ day.day_index }}
              </span>
              <span class="day-titles">
                <span class="day-title">第 {{ day.day_index }} 天</span>
                <span class="day-sub">{{ fmtDate(day.date) }} · {{ weekday(day.date) }}</span>
              </span>
              <span class="day-cost">¥{{ fmtMoney(dayCost(day)) }}</span>
              <span class="chevron">›</span>
            </button>

            <div class="day-body" v-show="!isCollapsed(day.day_index)">
              <div
                class="day-route-summary"
                v-if="daySummary[day.day_index]"
              >
                <span class="route-line-icon"></span>
                全程 {{ fmtDist(daySummary[day.day_index].distance) }} · 约 {{ fmtDur(daySummary[day.day_index].duration) }}
              </div>

              <div class="timeline">
                <div
                  v-for="(item, index) in day.items"
                  :key="item.id"
                  class="tl-node"
                >
                  <div class="rail">
                    <span
                      class="rail-dot"
                      :class="{ active: isActive(item) }"
                      :style="{ '--c': dayColor(day.day_index - 1) }"
                    >{{ index + 1 }}</span>
                    <span
                      class="rail-line"
                      v-if="index < day.items.length - 1"
                    ></span>
                  </div>

                  <div class="node-body">
                    <div
                      class="place-card"
                      :class="{ active: isActive(item) }"
                      :ref="(el) => setItemRef(item.id, el)"
                      @click="selectItem(item, day)"
                    >
                      <div class="place-card__top">
                        <span class="place-time">
                          <el-icon><Clock /></el-icon>
                          {{ item.start_time }} – {{ item.end_time }}
                        </span>
                        <span class="place-cost" v-if="Number(item.cost_estimate) > 0">
                          <el-icon><Ticket /></el-icon>
                          ¥{{ fmtMoney(item.cost_estimate) }}
                        </span>
                        <span class="place-cost free" v-else>免费</span>
                      </div>
                      <div class="place-name">{{ item.place_name }}</div>
                      <div class="place-hint" v-if="isActive(item)">点击右侧查看「周边推荐」</div>
                    </div>

                    <button
                      class="route-chip"
                      v-if="index < day.items.length - 1"
                      type="button"
                      :class="{ clickable: segSteps(day.day_index, index).length > 0 }"
                      @click.stop="toggleSegment(day.day_index, index)"
                    >
                      <template v-if="segmentOf(day.day_index, index)">
                        <span class="route-chip__icon" :class="`is-${travelMode}`">{{ travelModeIcon }}</span>
                        <span class="route-chip__body">
                          <span class="route-chip__title">
                            {{ lineTitle(day.day_index, index) || travelModeLabel }}
                            <em v-if="segmentOf(day.day_index, index)!.estimated">估算</em>
                          </span>
                          <span class="route-chip__meta">
                            约 {{ fmtDur(segmentOf(day.day_index, index)!.duration) }} ·
                            {{ fmtDist(segmentOf(day.day_index, index)!.distance) }}
                            <span
                              v-if="segmentOf(day.day_index, index)!.cost"
                              class="route-cost"
                            >· ¥{{ fmtMoney(segmentOf(day.day_index, index)!.cost) }}</span>
                          </span>
                        </span>
                        <span
                          v-if="segSteps(day.day_index, index).length"
                          class="route-more"
                        >{{ expandedSegment === segKey(day.day_index, index) ? '收起' : '详情' }}</span>
                      </template>
                      <template v-else-if="routesLoading">
                        <span class="route-chip__icon loading">···</span>
                        <span class="route-chip__body">
                          <span class="route-chip__title">正在计算{{ travelModeLabel }}路线…</span>
                        </span>
                      </template>
                      <template v-else>
                        <span class="route-chip__icon">—</span>
                        <span class="route-chip__body">
                          <span class="route-chip__title">
                            {{ travelMode === 'transit' ? '暂无公交换乘方案' : '暂无路线数据' }}
                          </span>
                        </span>
                      </template>
                    </button>

                    <!-- 换乘 / 途经详情 -->
                    <div
                      v-if="expandedSegment === segKey(day.day_index, index) && segSteps(day.day_index, index).length"
                      class="route-steps"
                    >
                      <div
                        v-for="(step, stepIndex) in segSteps(day.day_index, index)"
                        :key="stepIndex"
                        class="route-steps__item"
                      >
                        <span class="route-steps__icon" :class="`is-${step.mode}`">{{ stepIcon(step) }}</span>
                        <div class="route-steps__body">
                          <p class="route-steps__title">{{ stepTitle(step) }}</p>
                          <p class="route-steps__meta" v-if="stepMeta(step)">{{ stepMeta(step) }}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
      </aside>

      <!-- 中间：地图 -->
      <div class="center-panel">
        <div id="amap-container"></div>

        <!-- 天筛选 -->
        <div class="map-toolbar" v-if="!mapError">
          <button
            class="map-chip"
            :class="{ on: mapDay === 0 }"
            @click="setMapDay(0)"
          >全部</button>
          <button
            v-for="day in days"
            :key="day.day_index"
            class="map-chip"
            :class="{ on: mapDay === day.day_index }"
            :style="{ '--c': dayColor(day.day_index - 1) }"
            @click="setMapDay(day.day_index)"
          >第{{ day.day_index }}天</button>
        </div>

        <button class="map-fab" v-if="!mapError" title="查看全部地点" @click="fitAll(true)">
          <el-icon><FullScreen /></el-icon>
        </button>

        <div v-if="mapError" class="map-error">
          <div class="map-error__card">
            <span class="map-error__icon">🗺️</span>
            <p>{{ mapError }}</p>
            <el-button size="small" @click="retryMap">重试</el-button>
          </div>
        </div>
      </div>

      <!-- 右侧：预算 + 周边推荐 + AI 助手 -->
      <aside class="right-panel">
        <!-- 预算 -->
        <section class="budget-card">
          <div class="budget-head">
            <span>预算明细</span>
            <span class="budget-badge" v-if="budget">{{ budgetPercent }}%</span>
          </div>
          <div class="budget-amount">
            <span class="currency">¥</span>{{ fmtMoney(totalCost) }}
            <span class="budget-total" v-if="budget">/ ¥{{ fmtMoney(budget) }}</span>
          </div>
          <div class="budget-bar" v-if="budget">
            <i :style="{ width: budgetPercent + '%' }"></i>
          </div>
          <div class="budget-meta">
            <span v-if="budget">剩余 ¥{{ fmtMoney(budget - totalCost) }}</span>
            <span v-else>规划时未填写预算</span>
            <span v-if="travelers">人均 ¥{{ fmtMoney(totalCost / travelers) }}</span>
          </div>

          <ul class="day-budget">
            <li v-for="day in days" :key="day.day_index">
              <span class="dot" :style="{ background: dayColor(day.day_index - 1) }"></span>
              第 {{ day.day_index }} 天
              <span class="day-budget__value">¥{{ fmtMoney(dayCost(day)) }}</span>
            </li>
          </ul>
        </section>

        <!-- 周边推荐 -->
        <section class="nearby-card">
          <div class="nearby-head">
            <div>
              <h4>周边推荐</h4>
              <p class="nearby-sub">
                {{ activeItem ? `围绕「${activeItem.place_name}」` : '点击左侧地点查看附近' }}
              </p>
            </div>
            <el-icon class="nearby-icon"><LocationFilled /></el-icon>
          </div>

          <div class="nearby-tabs">
            <button
              v-for="cat in categories"
              :key="cat.key"
              class="nearby-tab"
              :class="{ on: nearbyCategory === cat.key }"
              @click="switchCategory(cat.key)"
            >{{ cat.label }}</button>
          </div>

          <div class="radius-row">
            <button
              v-for="r in radiusOptions"
              :key="r"
              class="radius-chip"
              :class="{ on: nearbyRadius === r }"
              @click="switchRadius(r)"
            >{{ r / 1000 }}km 内</button>
          </div>

          <div class="nearby-list" v-loading="nearbyLoading">
            <template v-if="nearby.length">
              <article
                v-for="poi in nearby"
                :key="poi.id"
                class="poi-card"
                :class="{ active: previewPoiId === poi.id }"
                @click="previewPoi(poi)"
              >
                <div
                  class="poi-thumb"
                  :style="poi.photo ? { backgroundImage: `url(${poi.photo})` } : {}"
                >
                  <span v-if="!poi.photo" class="poi-thumb__icon">{{ categoryFallback }}</span>
                </div>
                <div class="poi-body">
                  <div class="poi-name">{{ poi.name }}</div>
                  <div class="poi-meta">
                    <span class="poi-rating" v-if="poi.rating">★ {{ poi.rating }}</span>
                    <span class="poi-dist">{{ fmtDist(poi.distance) }}</span>
                  </div>
                  <div class="poi-addr">{{ poi.address || poi.type }}</div>
                </div>
                <button class="poi-add" title="加入当天行程" @click.stop="addPoi(poi)">+</button>
              </article>
            </template>
            <div v-else-if="!nearbyLoading" class="nearby-empty">
              <p v-if="!activeItem">先在上方选择一个地点吧</p>
              <p v-else>当前范围内暂无可推荐的地点</p>
            </div>
          </div>
        </section>

        <!-- AI 助手 -->
        <section class="assistant-card">
          <div class="assistant-head">
            <span class="assistant-avatar">AI</span>
            <div>
              <h4>AI 助手</h4>
              <p class="nearby-sub">说一句话就能调整行程</p>
            </div>
          </div>
          <el-input
            v-model="chatInput"
            type="textarea"
            :rows="2"
            resize="none"
            placeholder="比如：把第二天的景点换成室内的"
          />
          <el-button
            type="primary"
            class="assistant-btn"
            :loading="revising"
            @click="sendRevision"
          >发送修改指令</el-button>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Clock, Ticket, FullScreen, RefreshRight, LocationFilled } from '@element-plus/icons-vue'
import request from '../api/request'

type PageStatus = 'planning' | 'ready' | 'failed' | 'invalid'

interface TripItem {
  id: number
  place_name: string
  start_time: string
  end_time: string
  cost_estimate: number
  lng: number | null
  lat: number | null
}

interface TripDay {
  day_index: number
  date: string
  items: TripItem[]
}

interface TripData {
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

type TravelMode = 'driving' | 'transit' | 'walking'

interface RouteStep {
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

interface RouteInfo {
  distance: number
  duration: number
  points: [number, number][]
  estimated?: boolean
  mode?: string
  /** 打车预估车费 / 公交票价（元） */
  cost?: number | null
  steps?: RouteStep[]
}

interface NearbyPoi {
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

const route = useRoute()
const router = useRouter()
const tripId = route.query.trip_id

const status = ref<PageStatus>('planning')
const tripData = ref<TripData | null>(null)
const chatInput = ref('')
const revising = ref(false)

const days = computed<TripDay[]>(() => tripData.value?.days ?? [])
const stopCount = computed(() => days.value.reduce((sum, d) => sum + d.items.length, 0))
const totalCost = computed(() =>
  days.value.reduce(
    (sum, d) => sum + d.items.reduce((s, i) => s + Number(i.cost_estimate || 0), 0),
    0
  )
)
const budget = computed(() => {
  const value = Number(tripData.value?.budget)
  return Number.isFinite(value) && value > 0 ? value : null
})
const budgetPercent = computed(() =>
  budget.value ? Math.min(100, Math.round((totalCost.value / budget.value) * 100)) : 0
)
const travelers = computed(() => Number(tripData.value?.travelers) || 0)
const dateRange = computed(() => {
  const start = days.value[0]?.date
  const end = days.value[days.value.length - 1]?.date
  if (!start || !end) return ''
  return `${fmtDate(start)} → ${fmtDate(end)}`
})

// ---------- 小工具 ----------
const DAY_COLORS = ['#0ea5e9', '#f97316', '#8b5cf6', '#10b981', '#ef4444', '#f59e0b', '#06b6d4']

function dayColor(index: number) {
  return DAY_COLORS[((index % DAY_COLORS.length) + DAY_COLORS.length) % DAY_COLORS.length]
}

function fmtMoney(value: number | string | null | undefined) {
  const num = Number(value || 0)
  return num >= 1000 ? num.toLocaleString('zh-CN', { maximumFractionDigits: 0 }) : `${Math.round(num)}`
}

function fmtDist(meters: number) {
  if (!meters || meters <= 0) return '—'
  return meters >= 1000 ? `${(meters / 1000).toFixed(1)} km` : `${Math.round(meters)} m`
}

function fmtDur(seconds: number) {
  if (!seconds || seconds <= 0) return '—'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} 分钟`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m ? `${h} 小时 ${m} 分` : `${h} 小时`
}

function parseDate(dateStr?: string) {
  const [y, m, d] = (dateStr || '').split('-').map(Number)
  if (!y || !m || !d) return null
  return new Date(y, m - 1, d)
}

function fmtDate(dateStr?: string) {
  const date = parseDate(dateStr)
  if (!date) return dateStr || ''
  return `${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function weekday(dateStr?: string) {
  const date = parseDate(dateStr)
  if (!date) return ''
  return ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][date.getDay()]
}

function esc(text: string) {
  return String(text ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] as string)
  )
}

function hasCoords(item?: TripItem | null): boolean {
  return !!item && item.lng != null && item.lat != null
}

function dayCost(day: TripDay) {
  return day.items.reduce((sum, item) => sum + Number(item.cost_estimate || 0), 0)
}

// ---------- 折叠 / 展开 ----------
const collapsedDays = ref<number[]>([])
const isCollapsed = (index: number) => collapsedDays.value.includes(index)
const hasCollapsed = computed(() => collapsedDays.value.length > 0)

function toggleDay(index: number) {
  collapsedDays.value = isCollapsed(index)
    ? collapsedDays.value.filter((i) => i !== index)
    : [...collapsedDays.value, index]
}

function expandAll() {
  collapsedDays.value = []
}

// ---------- 选中地点 ----------
const activeItem = ref<TripItem | null>(null)
const activeDayIndex = ref(0)
const isActive = (item: TripItem) => activeItem.value?.id === item.id

const itemEls = new Map<number, HTMLElement>()
function setItemRef(id: number, el: any) {
  if (el) itemEls.set(id, el as HTMLElement)
  else itemEls.delete(id)
}

function selectItem(item: TripItem, day: TripDay) {
  activeItem.value = item
  activeDayIndex.value = day.day_index
  previewPoiId.value = ''
  clearNearbyMarkers()

  if (isCollapsed(day.day_index)) toggleDay(day.day_index)

  nextTick(() => {
    itemEls.get(item.id)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  })

  // 当前筛选把这一天隐藏了，就自动切回「全部」
  if (mapDay.value !== 0 && mapDay.value !== day.day_index) {
    mapDay.value = 0
    redrawOverlays()
  }

  highlightMarker(item.id)
  if (mapInstance.value && hasCoords(item)) {
    mapInstance.value.setZoomAndCenter(
      Math.max(mapInstance.value.getZoom(), 14),
      [item.lng, item.lat],
      false,
      350
    )
    openInfo(item, day)
  }

  loadNearby()
}

// ---------- 高德地图加载 ----------
const AMAP_KEY = import.meta.env.VITE_AMAP_JS_KEY as string | undefined
const AMAP_SECURITY_CODE = import.meta.env.VITE_AMAP_SECURITY_CODE as string | undefined

declare global {
  interface Window {
    _AMapSecurityConfig?: { securityJsCode: string }
    AMap?: any
    __amapLoadedKey?: string
    ___onAPILoaded?: (error?: unknown) => void
  }
}

let amapPromise: Promise<any> | null = null

function loadAMap(): Promise<any> {
  if (window.AMap) {
    if (window.__amapLoadedKey !== AMAP_KEY) {
      return Promise.reject(
        new Error('页面上的高德 SDK 是用旧 Key 加载的（热更新遗留），请按 Ctrl+Shift+R 强制刷新页面')
      )
    }
    return Promise.resolve(window.AMap)
  }
  if (amapPromise) return amapPromise

  amapPromise = new Promise((resolve, reject) => {
    window.___onAPILoaded = (error?: unknown) => {
      delete window.___onAPILoaded
      if (error) {
        amapPromise = null
        reject(new Error(String(error)))
        return
      }
      window.__amapLoadedKey = AMAP_KEY
      resolve(window.AMap)
    }

    const script = document.createElement('script')
    script.src =
      `https://webapi.amap.com/maps?callback=___onAPILoaded&v=2.0` +
      `&key=${encodeURIComponent(AMAP_KEY!)}&plugin=AMap.Scale,AMap.ToolBar`
    script.onerror = () => {
      amapPromise = null
      script.remove()
      reject(new Error('高德 JS API 脚本加载失败，请检查网络或 Key 的域名白名单'))
    }
    document.head.appendChild(script)
  })

  return amapPromise
}

// ---------- 地图实例与图层 ----------
let AMapLib: any = null
const mapInstance = ref<any>(null)
const mapError = ref('')
const mapDay = ref(0)

let dayMarkers: any[] = []
let dayPolylines: any[] = []
let nearbyMarkers: any[] = []
const markerEls = new Map<number, HTMLElement>()
let infoWindow: any = null
let previewInfo: any = null

const routes = ref<Record<string, RouteInfo>>({})
const routesLoading = ref(false)
let routesRequestSeq = 0

// ---------- 出行方式（打车 / 公交 / 步行） ----------
const travelModes = [
  { key: 'driving', label: '打车', icon: '🚕', desc: '按驾车路线估算耗时和车费' },
  { key: 'transit', label: '公交', icon: '🚇', desc: '公交 / 地铁换乘方案，可看具体怎么坐' },
  { key: 'walking', label: '步行', icon: '🚶', desc: '步行路线与耗时' }
] as const

const travelMode = ref<TravelMode>(readStoredTravelMode())
const expandedSegment = ref('')

function readStoredTravelMode(): TravelMode {
  const stored = localStorage.getItem('tp_travel_mode')
  return stored === 'transit' || stored === 'walking' ? stored : 'driving'
}
const travelModeLabel = computed(
  () => travelModes.find((m) => m.key === travelMode.value)?.label ?? '打车'
)
const travelModeIcon = computed(
  () => travelModes.find((m) => m.key === travelMode.value)?.icon ?? '🚕'
)

function segKey(dayIndex: number, index: number) {
  return `${dayIndex}-${index}`
}

function segSteps(dayIndex: number, index: number): RouteStep[] {
  return routes.value[segKey(dayIndex, index)]?.steps ?? []
}

function toggleSegment(dayIndex: number, index: number) {
  if (!segSteps(dayIndex, index).length) return
  const key = segKey(dayIndex, index)
  expandedSegment.value = expandedSegment.value === key ? '' : key
}

async function switchTravelMode(mode: TravelMode) {
  if (travelMode.value === mode) return
  travelMode.value = mode
  // 记住上次选的出行方式，下次打开工作台不用再切
  localStorage.setItem('tp_travel_mode', mode)
  expandedSegment.value = ''
  routes.value = {}
  await loadRoutes()
}

/** 公交模式下把线路名拼出来，比如「地铁4号线 → 113路」 */
function lineTitle(dayIndex: number, index: number) {
  const seg = routes.value[segKey(dayIndex, index)]
  if (!seg?.steps?.length) return ''
  const lines = seg.steps.filter((s) => s.line).map((s) => s.line as string)
  return [...new Set(lines)].join(' → ')
}

function stepIcon(step: RouteStep) {
  if (step.mode === 'walk') return '🚶'
  if (step.mode === 'subway') return '🚇'
  if (step.mode === 'bus') return '🚌'
  return '🚕'
}

function stepTitle(step: RouteStep) {
  if (step.mode === 'walk') return step.text || `步行 ${fmtDist(step.distance || 0)}`
  if (step.mode === 'bus' || step.mode === 'subway') {
    return `${step.line}　${step.from} → ${step.to}`
  }
  return step.text || '继续行驶'
}

function stepMeta(step: RouteStep) {
  if (step.mode === 'walk') return `步行 ${fmtDist(step.distance || 0)} · ${fmtDur(step.duration || 0)}`
  if (step.mode === 'bus' || step.mode === 'subway') {
    const parts = [`坐 ${step.stops || 0} 站`, fmtDur(step.duration || 0)]
    if (step.direction) parts.push(`往 ${step.direction}`)
    return parts.join(' · ')
  }
  return `行驶 ${fmtDist(step.distance || 0)} · ${fmtDur(step.duration || 0)}`
}

function segmentOf(dayIndex: number, index: number): RouteInfo | undefined {
  const real = routes.value[`${dayIndex}-${index}`]
  if (real && real.distance > 0) return real

  // 公交没有可用的直线估算，宁愿显示「暂无方案」也不给假数据
  if (travelMode.value === 'transit') return undefined

  // 高德没返回（限流 / 两点过近）时用直线距离估一个兜底值，保证列表里不会出现空白
  const day = days.value.find((d) => d.day_index === dayIndex)
  const from = day?.items[index]
  const to = day?.items[index + 1]
  if (!hasCoords(from) || !hasCoords(to)) return undefined

  const distance = haversine(from!.lng as number, from!.lat as number, to!.lng as number, to!.lat as number)
  // 步行按 4.7km/h；打车近距离起步慢，按 10km/h，远距离按 27km/h
  const speed =
    travelMode.value === 'walking' ? 1.3 : distance < 1200 ? 2.8 : 7.5
  return {
    distance: Math.round(distance),
    duration: Math.round(distance / speed),
    points: [],
    estimated: true,
    mode: travelMode.value
  }
}

function haversine(lng1: number, lat1: number, lng2: number, lat2: number) {
  const R = 6371000
  const toRad = (deg: number) => (deg * Math.PI) / 180
  const dLat = toRad(lat2 - lat1)
  const dLng = toRad(lng2 - lng1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(a))
}

const daySummary = computed<Record<number, { distance: number; duration: number }>>(() => {
  const summary: Record<number, { distance: number; duration: number }> = {}
  days.value.forEach((day) => {
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

async function ensureMap() {
  mapError.value = ''
  if (!AMAP_KEY) {
    mapError.value = '未配置高德地图 Key：请在 .env.local 填写 VITE_AMAP_JS_KEY 后重启 npm run dev。'
    return false
  }
  if (mapInstance.value) {
    mapInstance.value.resize()
    return true
  }

  if (AMAP_SECURITY_CODE) {
    window._AMapSecurityConfig = { securityJsCode: AMAP_SECURITY_CODE }
  }

  try {
    AMapLib = await loadAMap()
    const first = firstCoord()
    const map = new AMapLib.Map('amap-container', {
      zoom: 12,
      center: first || [116.397428, 39.90923],
      viewMode: '2D',
      mapStyle: 'amap://styles/whitesmoke',
      resizeEnable: true,
      showIndoorMap: false
    })
    mapInstance.value = map

    infoWindow = new AMapLib.InfoWindow({
      isCustom: true,
      offset: new AMapLib.Pixel(0, -6),
      autoMove: true
    })
    previewInfo = new AMapLib.InfoWindow({
      isCustom: true,
      offset: new AMapLib.Pixel(0, -6),
      autoMove: true
    })

    map.on('click', () => {
      infoWindow?.close()
    })
    map.on('zoomend', () => syncLabelVisibility())
    if (AMapLib.Scale) {
      map.addControl(new AMapLib.Scale({ position: 'LB' }))
    }
    return true
  } catch (e: any) {
    console.error('高德地图加载失败', e)
    mapError.value = `地图加载失败：${e?.message || e}（请检查 Key 是否为「Web端(JS API)」类型、安全密钥是否匹配）`
    return false
  }
}

function firstCoord(): [number, number] | null {
  for (const day of days.value) {
    for (const item of day.items) {
      if (hasCoords(item)) return [item.lng as number, item.lat as number]
    }
  }
  return null
}

async function retryMap() {
  mapInstance.value?.destroy?.()
  mapInstance.value = null
  amapPromise = null
  const ok = await ensureMap()
  if (ok) {
    redrawOverlays()
    fitAll()
  }
}

function setMapDay(index: number) {
  mapDay.value = index
  redrawOverlays()
  nextTick(() => fitAll(false))

  // 切到某一天时，如果当前选中的地点不属于这一天，就把焦点换成这天的第一个地点
  if (index !== 0) {
    const day = days.value.find((d) => d.day_index === index)
    if (day && day.items.length && !day.items.some((i) => i.id === activeItem.value?.id)) {
      activeItem.value = day.items.find((i) => hasCoords(i)) ?? day.items[0]
      activeDayIndex.value = day.day_index
      infoWindow?.close()
      previewPoiId.value = ''
      clearNearbyMarkers()
      nextTick(() => highlightMarker(activeItem.value?.id))
      loadNearby()
    }
  }
}

function redrawOverlays() {
  const map = mapInstance.value
  if (!map || !AMapLib) return

  if (dayMarkers.length || dayPolylines.length) {
    map.remove([...dayMarkers, ...dayPolylines])
  }
  dayMarkers = []
  dayPolylines = []
  markerEls.clear()

  const visibleDays =
    mapDay.value === 0 ? days.value : days.value.filter((d) => d.day_index === mapDay.value)

  visibleDays.forEach((day) => {
    const color = dayColor(day.day_index - 1)
    const items = day.items

    // 1. 先画路线（放在标记下面）
    items.forEach((item, index) => {
      if (index >= items.length - 1) return
      const from = item
      const to = items[index + 1]
      if (!hasCoords(from) || !hasCoords(to)) return

      const seg = segmentOf(day.day_index, index)
      const hasPath = !!seg?.points?.length
      const path = hasPath
        ? seg!.points.map((p) => [p[0], p[1]])
        : [
            [from.lng as number, from.lat as number],
            [to.lng as number, to.lat as number]
          ]

      const highlighted = activeItem.value?.id === from.id

      // 白色描边，让路线在地图底色上更清晰
      dayPolylines.push(
        new AMapLib.Polyline({
          path,
          strokeColor: '#ffffff',
          strokeWeight: 9,
          strokeOpacity: 0.9,
          lineJoin: 'round',
          lineCap: 'round',
          zIndex: 50
        })
      )

      dayPolylines.push(
        new AMapLib.Polyline({
          path,
          strokeColor: hasPath ? color : '#94a3b8',
          strokeWeight: highlighted ? 7 : 5,
          strokeOpacity: 0.95,
          strokeStyle: hasPath ? 'solid' : 'dashed',
          showDir: hasPath,
          lineJoin: 'round',
          lineCap: 'round',
          zIndex: 51
        })
      )
    })

    // 2. 再画标记
    items.forEach((item, index) => {
      if (!hasCoords(item)) return

      const content = document.createElement('div')
      content.className = 'tp-marker'
      content.style.setProperty('--c', color)
      content.innerHTML =
        `<span class="tp-marker__pin">${index + 1}</span>` +
        `<span class="tp-marker__label">${esc(item.place_name)}</span>`

      const marker = new AMapLib.Marker({
        position: [item.lng, item.lat],
        content,
        anchor: 'center',
        zIndex: 100 + index,
        extData: { itemId: item.id }
      })

      marker.on('click', () => selectItem(item, day))
      dayMarkers.push(marker)

      markerEls.set(item.id, content)
      if (isActive(item)) content.classList.add('is-active')
    })
  })

  if (dayMarkers.length || dayPolylines.length) {
    map.add([...dayPolylines, ...dayMarkers])
  }
  highlightMarker(activeItem.value?.id)
}

function highlightMarker(itemId?: number) {
  markerEls.forEach((el, id) => {
    el.classList.toggle('is-active', id === itemId)
  })
  syncLabelVisibility()
}

/** 地图缩得很小时隐藏地名标签，避免几十个标注糊成一团；悬停仍可看到 */
function syncLabelVisibility() {
  const zoom = mapInstance.value?.getZoom?.() ?? 12
  const showAll = zoom >= 13.5
  markerEls.forEach((el, id) => {
    el.classList.toggle('label-hidden', !showAll && id !== activeItem.value?.id)
  })
}

function fitAll(animate = true) {
  const map = mapInstance.value
  if (!map) return
  const overlays = [...dayMarkers, ...dayPolylines]
  if (overlays.length) {
    map.setFitView(overlays, !animate, [80, 80, 80, 80], 15)
  }
}

function openInfo(item: TripItem, day: TripDay) {
  if (!mapInstance.value || !infoWindow || !hasCoords(item)) return
  const color = dayColor(day.day_index - 1)
  const price =
    Number(item.cost_estimate) > 0
      ? `<div class="tp-info__row">门票预估 ¥${fmtMoney(item.cost_estimate)}</div>`
      : ''
  infoWindow.setContent(
    `<div class="tp-info">` +
      `<div class="tp-info__head"><span class="tp-info__dot" style="background:${color}"></span>${esc(item.place_name)}</div>` +
      `<div class="tp-info__row">🕘 ${esc(item.start_time)} – ${esc(item.end_time)}</div>` +
      price +
      `<div class="tp-info__foot">第 ${day.day_index} 天 · ${fmtDate(day.date)}</div>` +
      `</div>`
  )
  infoWindow.open(mapInstance.value, [item.lng, item.lat])
}

// ---------- 路线数据 ----------
async function loadRoutes() {
  const segs: { key: string; origin: string; destination: string }[] = []
  days.value.forEach((day) => {
    const items = day.items
    for (let i = 0; i < items.length - 1; i++) {
      const from = items[i]
      const to = items[i + 1]
      if (!hasCoords(from) || !hasCoords(to)) continue
      segs.push({
        key: `${day.day_index}-${i}`,
        origin: `${from.lng},${from.lat}`,
        destination: `${to.lng},${to.lat}`
      })
    }
  })

  const seq = ++routesRequestSeq
  if (!segs.length) {
    routes.value = {}
    return
  }

  routesLoading.value = true
  try {
    const res: any = await request.post('/api/v1/routes', {
      // 公交规划需要城市，直接用行程目的地
      city: tripData.value?.destination || '',
      segments: segs.map((s) => ({
        origin: s.origin,
        destination: s.destination,
        mode: travelMode.value
      }))
    })
    if (seq !== routesRequestSeq) return
    const next: Record<string, RouteInfo> = {}
    segs.forEach((seg, i) => {
      const data = res?.routes?.[i]
      if (data) next[seg.key] = data
    })
    routes.value = next
    redrawOverlays()
  } catch (error) {
    console.warn('路线计算失败，改为直线连接', error)
  } finally {
    if (seq === routesRequestSeq) routesLoading.value = false
  }
}

// ---------- 周边推荐 ----------
const categories = [
  { key: 'scenic', label: '景点' },
  { key: 'food', label: '美食' },
  { key: 'hotel', label: '住宿' },
  { key: 'shopping', label: '购物' }
]
const radiusOptions = [1000, 2000, 5000]

const nearby = ref<NearbyPoi[]>([])
const nearbyLoading = ref(false)
const nearbyCategory = ref('scenic')
const nearbyRadius = ref(2000)
const previewPoiId = ref('')

const categoryFallback = computed(
  () => ({ scenic: '🏞', food: '🍜', hotel: '🏨', shopping: '🛍' }[nearbyCategory.value] ?? '📍')
)

let nearbySeq = 0

async function loadNearby() {
  const item = activeItem.value
  const seq = ++nearbySeq
  if (!item || !hasCoords(item)) {
    nearby.value = []
    return
  }

  nearbyLoading.value = true
  try {
    const res: any = await request.get('/api/v1/pois/nearby', {
      params: {
        lng: item.lng,
        lat: item.lat,
        category: nearbyCategory.value,
        radius: nearbyRadius.value,
        limit: 10
      }
    })
    if (seq !== nearbySeq) return
    nearby.value = res?.pois ?? []
  } catch (error) {
    if (seq !== nearbySeq) return
    nearby.value = []
    ElMessage.error('周边推荐加载失败，请稍后再试')
  } finally {
    if (seq === nearbySeq) nearbyLoading.value = false
  }
}

function switchCategory(key: string) {
  if (nearbyCategory.value === key) return
  nearbyCategory.value = key
  previewPoiId.value = ''
  clearNearbyMarkers()
  loadNearby()
}

function switchRadius(value: number) {
  if (nearbyRadius.value === value) return
  nearbyRadius.value = value
  loadNearby()
}

function clearNearbyMarkers() {
  if (nearbyMarkers.length) {
    mapInstance.value?.remove(nearbyMarkers)
    nearbyMarkers = []
  }
  previewInfo?.close()
}

function previewPoi(poi: NearbyPoi) {
  const map = mapInstance.value
  if (!map || !AMapLib) return
  previewPoiId.value = poi.id
  clearNearbyMarkers()

  const content = document.createElement('div')
  content.className = 'tp-marker tp-marker--poi'
  content.innerHTML = `<span class="tp-marker__pin">★</span>`

  const marker = new AMapLib.Marker({
    position: [poi.lng, poi.lat],
    content,
    anchor: 'center',
    zIndex: 300
  })
  nearbyMarkers.push(marker)
  map.add(marker)

  map.setZoomAndCenter(Math.max(map.getZoom(), 15), [poi.lng, poi.lat], false, 300)

  previewInfo?.setContent(
    `<div class="tp-info tp-info--poi">` +
      `<div class="tp-info__head">${esc(poi.name)}</div>` +
      `<div class="tp-info__row">${poi.rating ? `★ ${esc(poi.rating)} · ` : ''}距此 ${fmtDist(poi.distance)}</div>` +
      (poi.address ? `<div class="tp-info__row tp-info__row--muted">${esc(poi.address)}</div>` : '') +
      `</div>`
  )
  previewInfo?.open(map, [poi.lng, poi.lat])
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
      cost_estimate: 0
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
    const res: any = await request.get(`/api/v1/trips/${tripId}`)
    const previousId = activeItem.value?.id
    tripData.value = res
    status.value = 'ready'

    await nextTick()
    const ok = await ensureMap()
    if (ok) {
      redrawOverlays()
      if (resetView) fitAll()
    }

    // 保持之前选中的地点（刷新后 id 可能变化，按名字兜底）
    const allItems = days.value.flatMap((d) => d.items)
    const keep =
      allItems.find((i) => i.id === previousId) ??
      allItems.find((i) => i.place_name === activeItem.value?.place_name) ??
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

async function sendRevision() {
  if (!chatInput.value.trim()) {
    ElMessage.warning('先说说你想怎么调整吧')
    return
  }
  revising.value = true
  try {
    await request.post(`/api/v1/trips/${tripId}/revisions`, { instruction: chatInput.value.trim() })
    ElMessage.success('修改指令已发送，正在重新规划…')
    chatInput.value = ''
  } catch (error) {
    console.error('修改失败', error)
    ElMessage.error('发送失败，请稍后再试')
  } finally {
    revising.value = false
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
  clearNearbyMarkers()
  if (mapInstance.value) {
    mapInstance.value.destroy()
    mapInstance.value = null
  }
  dayMarkers = []
  dayPolylines = []
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

/* ---------- 顶栏 ---------- */
.top-bar {
  height: 62px;
  flex: 0 0 62px;
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid var(--line);
  z-index: 20;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}
.brand-mark {
  width: 34px;
  height: 34px;
  border-radius: 11px;
  background: linear-gradient(135deg, #14b8a6, #0d9488);
  color: #fff;
  font-size: 17px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 16px rgba(13, 148, 136, 0.28);
}
.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}
.brand-name {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.3px;
}
.brand-sub {
  font-size: 11px;
  color: var(--muted);
  letter-spacing: 1.5px;
}
.trip-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}
.pill {
  font-size: 12px;
  color: var(--muted);
  background: #f4f7f8;
  border: 1px solid var(--line);
  padding: 5px 11px;
  border-radius: 999px;
  white-space: nowrap;
}
.pill--dest {
  color: var(--teal-dark);
  background: var(--teal-soft);
  border-color: #c9f0e8;
  font-weight: 600;
}
.badge-done {
  font-size: 12px;
  color: #fff;
  background: linear-gradient(135deg, #10b981, #0d9488);
  padding: 5px 12px;
  border-radius: 999px;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
}
.ghost-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--muted);
  background: #fff;
  border: 1px solid var(--line);
  padding: 8px 14px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.18s;
}
.ghost-btn:hover {
  color: var(--teal-dark);
  border-color: #b8e6df;
  background: var(--teal-soft);
}

/* ---------- 状态页 ---------- */
.state-page {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.planning-card {
  width: 460px;
  max-width: 92vw;
  background: #fff;
  border-radius: 20px;
  padding: 40px 36px 32px;
  text-align: center;
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
}
.planning-card h3 {
  margin: 22px 0 8px;
  font-size: 17px;
}
.planning-card p {
  margin: 0;
  font-size: 13px;
  color: var(--muted);
  line-height: 1.7;
}
.orbit {
  position: relative;
  width: 84px;
  height: 84px;
  margin: 0 auto;
}
.orbit-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px dashed #b8e6df;
  animation: spin 6s linear infinite;
}
.orbit-plane {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  animation: float 2.4s ease-in-out infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@keyframes float {
  0%,
  100% {
    transform: translateY(-3px);
  }
  50% {
    transform: translateY(3px);
  }
}
.skeleton-lines {
  margin-top: 22px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: center;
}
.skeleton-lines i {
  display: block;
  height: 8px;
  border-radius: 999px;
  background: linear-gradient(90deg, #eef2f5, #e2e8ee, #eef2f5);
  background-size: 200% 100%;
  animation: shimmer 1.6s linear infinite;
}
@keyframes shimmer {
  to {
    background-position: -200% 0;
  }
}

/* ---------- 主体三栏 ---------- */
.main-content {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
}

/* ---------- 左栏 ---------- */
.left-panel {
  width: 352px;
  flex: 0 0 352px;
  background: #fff;
  border-right: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.panel-head {
  padding: 18px 18px 12px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
.panel-head h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}
.panel-sub {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--muted);
}
.mini-btn {
  font-size: 12px;
  color: var(--teal-dark);
  background: var(--teal-soft);
  border: none;
  padding: 5px 10px;
  border-radius: 8px;
  cursor: pointer;
}
/* 出行方式切换 */
.mode-bar {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  padding: 0 18px 12px;
}
.mode-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 32px;
  border-radius: 9px;
  border: 1px solid var(--line);
  background: #fff;
  font-family: inherit;
  font-size: 12px;
  color: var(--muted);
  cursor: pointer;
  transition: all 0.16s;
}
.mode-btn:hover {
  border-color: #99f6e4;
  color: var(--teal-dark);
}
.mode-btn.on {
  background: var(--teal-soft);
  border-color: #99f6e4;
  color: var(--teal-dark);
  font-weight: 600;
}
.mode-btn__icon {
  font-size: 13px;
  line-height: 1;
}

.panel-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px 24px;
  scrollbar-width: thin;
}.panel-scroll::-webkit-scrollbar {
  width: 6px;
}
.panel-scroll::-webkit-scrollbar-thumb {
  background: #dbe4e9;
  border-radius: 3px;
}

.day-section {
  margin-bottom: 10px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #fff;
  overflow: hidden;
  transition: box-shadow 0.2s;
}
.day-section:not(.collapsed) {
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
}
.day-head {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 12px;
  background: #fbfdfd;
  border: none;
  cursor: pointer;
  text-align: left;
}
.day-head:hover {
  background: #f5faf9;
}
.day-badge {
  width: 28px;
  height: 28px;
  border-radius: 9px;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 28px;
}
.day-titles {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
  flex: 1;
  min-width: 0;
}
.day-title {
  font-size: 13.5px;
  font-weight: 600;
}
.day-sub {
  font-size: 11.5px;
  color: var(--muted);
}
.day-cost {
  font-size: 12px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.chevron {
  color: #cbd5e1;
  font-size: 16px;
  transition: transform 0.2s;
  line-height: 1;
}
.day-section.collapsed .chevron {
  transform: rotate(-90deg);
}
.day-body {
  padding: 6px 12px 12px;
}
.day-route-summary {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: var(--teal-dark);
  background: var(--teal-soft);
  border-radius: 8px;
  padding: 5px 9px;
  margin: 2px 0 10px;
}
.route-line-icon {
  width: 14px;
  height: 2px;
  border-radius: 1px;
  background: repeating-linear-gradient(90deg, var(--teal) 0 4px, transparent 4px 7px);
}

.timeline {
  display: flex;
  flex-direction: column;
}
.tl-node {
  display: grid;
  grid-template-columns: 26px 1fr;
  gap: 8px;
}
.rail {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.rail-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2px solid var(--c, var(--teal));
  background: #fff;
  color: var(--c, var(--teal));
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 22px;
  margin-top: 11px;
  transition: all 0.2s;
}
.rail-dot.active {
  background: var(--c, var(--teal));
  color: #fff;
  box-shadow: 0 0 0 4px rgba(13, 148, 136, 0.12);
}
.rail-line {
  flex: 1;
  width: 2px;
  background: repeating-linear-gradient(180deg, #d7e2e8 0 4px, transparent 4px 8px);
  border-radius: 1px;
  margin: 3px 0;
}
.node-body {
  padding-bottom: 2px;
}
.place-card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 9px 11px 10px;
  cursor: pointer;
  transition: all 0.18s;
}
.place-card:hover {
  border-color: #b8e6df;
  box-shadow: 0 6px 16px rgba(13, 148, 136, 0.08);
  transform: translateY(-1px);
}
.place-card.active {
  border-color: var(--teal);
  background: linear-gradient(90deg, #f0fdfa, #ffffff);
  box-shadow: inset 3px 0 0 var(--teal), 0 8px 20px rgba(13, 148, 136, 0.12);
}
.place-card__top {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11.5px;
  color: var(--muted);
}
.place-time {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-variant-numeric: tabular-nums;
}
.place-cost {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  margin-left: auto;
  color: var(--orange);
}
.place-cost.free {
  color: #94a3b8;
}
.place-name {
  margin-top: 4px;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.35;
  color: var(--ink);
}
.place-hint {
  margin-top: 6px;
  font-size: 11px;
  color: var(--teal-dark);
  background: var(--teal-soft);
  border-radius: 6px;
  padding: 3px 7px;
  display: inline-block;
}
.route-chip {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  text-align: left;
  font-family: inherit;
  font-size: 11.5px;
  color: var(--muted);
  background: #f8fbfc;
  border: 1px dashed #dbe4e9;
  border-radius: 12px;
  padding: 7px 10px;
  margin: 6px 0 6px 4px;
  cursor: default;
  transition: all 0.16s;
}
.route-chip__icon {
  width: 22px;
  height: 22px;
  flex: 0 0 22px;
  display: grid;
  place-items: center;
  border-radius: 7px;
  background: #fff;
  border: 1px solid #e2e8f0;
  font-size: 12px;
}
.route-chip__icon.loading {
  color: #f59e0b;
  animation: blink 1s ease-in-out infinite;
}
@keyframes blink {
  50% {
    opacity: 0.2;
  }
}
.route-chip__body {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 2px;
}
.route-chip__title {
  font-size: 12px;
  font-weight: 500;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.route-chip__title em {
  font-style: normal;
  font-size: 10px;
  font-weight: 400;
  color: #94a3b8;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 0 3px;
  margin-left: 4px;
}
.route-chip__meta {
  font-size: 11px;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sep {
  opacity: 0.4;
}
.route-chip.clickable {
  cursor: pointer;
}
.route-chip.clickable:hover {
  border-color: #99f6e4;
  background: #f0fdfa;
}
.route-cost {
  color: #b45309;
  font-weight: 600;
}
.route-more {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--teal-dark);
  background: var(--teal-soft);
  border-radius: 6px;
  padding: 2px 6px;
}

/* 换乘 / 途经详情 */
.route-steps {
  margin: 2px 0 8px 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #f8fbfc;
  border: 1px solid #e8f0f4;
  display: grid;
  gap: 10px;
}
.route-steps__item {
  display: flex;
  gap: 9px;
  align-items: flex-start;
}
.route-steps__icon {
  width: 24px;
  height: 24px;
  flex: 0 0 24px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  font-size: 12px;
  background: #fff;
  border: 1px solid #e2e8f0;
}
.route-steps__icon.is-subway {
  background: #eef2ff;
  border-color: #c7d2fe;
}
.route-steps__icon.is-bus {
  background: #ecfdf5;
  border-color: #a7f3d0;
}
.route-steps__title {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: #1e293b;
  word-break: break-word;
}
.route-steps__meta {
  margin: 2px 0 0;
  font-size: 11px;
  line-height: 1.4;
  color: var(--muted);
}

/* ---------- 中间地图 ---------- */
.center-panel {
  flex: 1;
  position: relative;
  min-width: 0;
  background: #e9eef1;
}
#amap-container {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.map-toolbar {
  position: absolute;
  top: 16px;
  left: 16px;
  display: flex;
  gap: 6px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(10px);
  padding: 6px;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
  z-index: 10;
}
.map-chip {
  border: none;
  background: transparent;
  color: var(--muted);
  font-size: 12.5px;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.16s;
}
.map-chip:hover {
  background: #f1f5f7;
}
.map-chip.on {
  background: var(--c, var(--teal));
  color: #fff;
  font-weight: 600;
  box-shadow: 0 4px 10px rgba(13, 148, 136, 0.25);
}
.map-fab {
  position: absolute;
  right: 16px;
  bottom: 22px;
  width: 42px;
  height: 42px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--teal-dark);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
  z-index: 10;
  transition: all 0.16s;
}
.map-fab:hover {
  background: var(--teal-soft);
  transform: translateY(-1px);
}
.map-error {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f4f7f8;
  z-index: 5;
}
.map-error__card {
  max-width: 460px;
  text-align: center;
  background: #fff;
  border-radius: 16px;
  padding: 28px 30px;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
}
.map-error__icon {
  font-size: 30px;
}
.map-error__card p {
  margin: 12px 0 16px;
  font-size: 13px;
  color: var(--muted);
  line-height: 1.7;
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

.budget-card {
  border-radius: 16px;
  padding: 16px;
  background: linear-gradient(135deg, #0f766e 0%, #0d9488 55%, #14b8a6 100%);
  color: #fff;
  box-shadow: 0 12px 28px rgba(13, 148, 136, 0.25);
}
.budget-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12.5px;
  opacity: 0.92;
  letter-spacing: 0.4px;
}
.budget-badge {
  font-size: 11px;
  background: rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  padding: 2px 9px;
}
.budget-amount {
  margin-top: 10px;
  font-size: 27px;
  font-weight: 700;
  letter-spacing: 0.5px;
  display: flex;
  align-items: baseline;
  gap: 3px;
  font-variant-numeric: tabular-nums;
}
.currency {
  font-size: 16px;
  font-weight: 500;
  opacity: 0.85;
}
.budget-total {
  font-size: 12.5px;
  font-weight: 400;
  opacity: 0.7;
  margin-left: 4px;
}
.budget-bar {
  margin-top: 12px;
  height: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.22);
  overflow: hidden;
}
.budget-bar i {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #fef08a, #fbbf24);
  transition: width 0.5s ease;
}
.budget-meta {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  font-size: 11.5px;
  opacity: 0.85;
}
.day-budget {
  list-style: none;
  margin: 14px 0 0;
  padding: 12px 0 0;
  border-top: 1px solid rgba(255, 255, 255, 0.18);
  display: grid;
  gap: 6px;
}
.day-budget li {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  opacity: 0.95;
}
.day-budget .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}
.day-budget__value {
  margin-left: auto;
  font-variant-numeric: tabular-nums;
}

.nearby-card {
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1 1 auto;
  min-height: 0;
}
.nearby-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.nearby-head h4,
.assistant-head h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
}
.nearby-sub {
  margin: 3px 0 0;
  font-size: 11.5px;
  color: var(--muted);
  max-width: 230px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.nearby-icon {
  color: #cbd5e1;
  font-size: 16px;
}
.nearby-tabs {
  display: flex;
  gap: 4px;
  background: #f4f7f8;
  border-radius: 10px;
  padding: 3px;
}
.nearby-tab {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 12px;
  color: var(--muted);
  padding: 7px 0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.16s;
}
.nearby-tab.on {
  background: #fff;
  color: var(--teal-dark);
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
}
.radius-row {
  display: flex;
  gap: 6px;
}
.radius-chip {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--muted);
  font-size: 11px;
  padding: 3px 9px;
  border-radius: 999px;
  cursor: pointer;
}
.radius-chip.on {
  border-color: #b8e6df;
  background: var(--teal-soft);
  color: var(--teal-dark);
  font-weight: 600;
}
.nearby-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1 1 auto;
  min-height: 60px;
  overflow-y: auto;
  padding-right: 2px;
  scrollbar-width: thin;
}
.nearby-list::-webkit-scrollbar {
  width: 5px;
}
.nearby-list::-webkit-scrollbar-thumb {
  background: #dbe4e9;
  border-radius: 3px;
}
.poi-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: 12px;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.16s;
  position: relative;
}
.poi-card:hover {
  background: #f8fbfc;
  border-color: var(--line);
}
.poi-card.active {
  background: var(--teal-soft);
  border-color: #b8e6df;
}
.poi-thumb {
  width: 48px;
  height: 48px;
  flex: 0 0 48px;
  border-radius: 10px;
  background: linear-gradient(135deg, #d7f2ec, #e8eef2);
  background-size: cover;
  background-position: center;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
  color: var(--teal-dark);
  overflow: hidden;
}
.poi-thumb__icon {
  font-size: 20px;
  line-height: 1;
}
.poi-body {
  min-width: 0;
  flex: 1;
}
.poi-name {
  font-size: 12.5px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.poi-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--muted);
  margin-top: 2px;
}
.poi-rating {
  color: #f59e0b;
  font-weight: 600;
}
.poi-addr {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.poi-add {
  width: 24px;
  height: 24px;
  flex: 0 0 24px;
  border-radius: 8px;
  border: 1px solid #d5e8e4;
  background: #fff;
  color: var(--teal-dark);
  font-size: 15px;
  line-height: 1;
  cursor: pointer;
  opacity: 0;
  transition: all 0.16s;
}
.poi-card:hover .poi-add {
  opacity: 1;
}
.poi-add:hover {
  background: var(--teal);
  border-color: var(--teal);
  color: #fff;
}
.nearby-empty {
  text-align: center;
  color: #a8b4bf;
  font-size: 12px;
  padding: 26px 0;
}

.assistant-card {
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 0 0 auto;
  background: linear-gradient(180deg, #fbfdfd, #ffffff);
}
.assistant-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.assistant-avatar {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.assistant-btn {
  width: 100%;
  border-radius: 10px;
}
:deep(.el-textarea__inner) {
  border-radius: 10px;
  font-size: 12.5px;
  box-shadow: 0 0 0 1px var(--line) inset;
}
:deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 1px var(--teal) inset;
}

/* ---------- 响应式 ---------- */
@media (max-width: 1440px) {
  .left-panel {
    width: 320px;
    flex-basis: 320px;
  }
  .right-panel {
    width: 312px;
    flex-basis: 312px;
  }
}
@media (max-width: 1180px) {
  .left-panel {
    width: 288px;
    flex-basis: 288px;
  }
  .right-panel {
    width: 286px;
    flex-basis: 286px;
  }
  .trip-meta .pill:nth-child(3) {
    display: none;
  }
}
</style>

<!-- 地图标记 / 信息窗体是注入到地图容器里的，不受 scoped 约束，放在这里 -->
<style>
.tp-marker {
  position: relative;
  width: 30px;
  height: 30px;
  cursor: pointer;
}
.tp-marker__pin {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--c, #0d9488);
  border: 3px solid #fff;
  color: #fff;
  font-size: 12.5px;
  font-weight: 700;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.28);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.tp-marker__label {
  position: absolute;
  top: 34px;
  left: 50%;
  transform: translateX(-50%);
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
  font-family: 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
  color: #0f172a;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid #e8eef2;
  border-radius: 6px;
  padding: 1px 6px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.1);
  pointer-events: none;
}
.tp-marker:hover .tp-marker__pin {
  transform: scale(1.08);
}
.tp-marker.is-active .tp-marker__pin {
  transform: scale(1.16);
  box-shadow: 0 0 0 6px color-mix(in srgb, var(--c, #0d9488) 22%, transparent),
    0 8px 20px rgba(15, 23, 42, 0.3);
  z-index: 5;
}
.tp-marker.is-active .tp-marker__label {
  border-color: var(--c, #0d9488);
  font-weight: 600;
}
.tp-marker.label-hidden .tp-marker__label {
  display: none;
}
.tp-marker.label-hidden:hover .tp-marker__label {
  display: block;
}
.tp-marker--poi .tp-marker__pin {
  --c: #f97316;
  background: #fff;
  color: #f97316;
  border-color: #f97316;
  animation: tp-pulse 1.8s ease-in-out infinite;
}
@keyframes tp-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(249, 115, 22, 0.45);
  }
  50% {
    box-shadow: 0 0 0 9px rgba(249, 115, 22, 0);
  }
}

.tp-info {
  min-width: 170px;
  max-width: 240px;
  background: #fff;
  border-radius: 12px;
  padding: 11px 13px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.18);
  font-family: 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
}
.tp-info__head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13.5px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.35;
}
.tp-info__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex: 0 0 7px;
}
.tp-info__row {
  margin-top: 5px;
  font-size: 11.5px;
  color: #475569;
}
.tp-info__row--muted {
  color: #94a3b8;
}
.tp-info__foot {
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed #e8eef2;
  font-size: 11px;
  color: #94a3b8;
}
</style>
