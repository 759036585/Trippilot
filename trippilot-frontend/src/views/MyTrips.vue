<!-- src/views/MyTrips.vue 我的行程历史 -->
<template>
  <div class="trips-page">
    <AppHeader solid />

    <main class="container">
      <header class="page-head">
        <div>
          <h1>我的行程</h1>
          <p v-if="userStore.isLoggedIn">
            {{ userStore.displayName }}，这里保存了你规划过的所有旅程
          </p>
          <p v-else>登录后即可查看行程历史</p>
        </div>
        <div class="page-head__actions">
          <button class="btn btn--ghost" type="button" :disabled="loading" @click="load(true)">
            <el-icon><RefreshRight /></el-icon>刷新
          </button>
          <button class="btn btn--primary" type="button" @click="router.push('/create')">
            <el-icon><Plus /></el-icon>新建行程
          </button>
        </div>
      </header>

      <!-- 加载骨架 -->
      <div v-if="loading && !trips.length" class="grid">
        <div v-for="n in 3" :key="n" class="skeleton">
          <div class="skeleton__cover"></div>
          <div class="skeleton__line skeleton__line--lg"></div>
          <div class="skeleton__line"></div>
          <div class="skeleton__line skeleton__line--sm"></div>
        </div>
      </div>

      <!-- 加载失败 -->
      <div v-else-if="errorText" class="state">
        <div class="state__icon">⚠️</div>
        <h3>行程加载失败</h3>
        <p>{{ errorText }}</p>
        <button class="btn btn--primary" type="button" @click="load(true)">重新加载</button>
      </div>

      <!-- 空状态 -->
      <div v-else-if="!trips.length" class="state">
        <div class="state__icon">🧳</div>
        <h3>还没有行程记录</h3>
        <p>告诉 AI 你想去哪、玩几天，几秒钟就能生成一份行程。</p>
        <button class="btn btn--primary" type="button" @click="router.push('/create')">
          <el-icon><MagicStick /></el-icon>开始规划第一个行程
        </button>
      </div>

      <!-- 行程列表 -->
      <div v-else class="grid">
        <article
          v-for="trip in trips"
          :key="trip.trip_id"
          class="trip-card"
          @click="openTrip(trip)"
        >
          <div class="trip-card__cover" :style="{ background: themeOf(trip.destination).gradient }">
            <span class="trip-card__emoji">{{ themeOf(trip.destination).emoji }}</span>
            <span class="trip-card__status" :class="`is-${trip.status}`">
              {{ statusText(trip.status) }}
            </span>
            <span class="trip-card__no">#{{ trip.trip_id }}</span>
          </div>

          <div class="trip-card__body">
            <div class="trip-card__title">
              <h3>{{ trip.destination || '未命名行程' }}</h3>
              <el-icon class="trip-card__arrow"><ArrowRight /></el-icon>
            </div>
            <p class="trip-card__date">
              <el-icon><Calendar /></el-icon>
              {{ formatRange(trip.start_date, trip.end_date) }}
            </p>

            <div class="trip-card__stats">
              <div class="stat">
                <span class="stat__value">{{ trip.day_count }}</span>
                <span class="stat__label">天</span>
              </div>
              <div class="stat">
                <span class="stat__value">{{ trip.item_count }}</span>
                <span class="stat__label">个地点</span>
              </div>
              <div class="stat">
                <span class="stat__value">{{ trip.travelers || 1 }}</span>
                <span class="stat__label">人</span>
              </div>
              <div class="stat stat--cost">
                <span class="stat__value">¥{{ formatMoney(trip.total_cost) }}</span>
                <span class="stat__label">预估花费</span>
              </div>
            </div>

            <div v-if="trip.budget" class="trip-card__budget">
              <div class="budget__bar">
                <span :style="{ width: budgetPercent(trip) + '%' }"></span>
              </div>
              <span class="budget__text">预算 ¥{{ formatMoney(trip.budget) }}</span>
            </div>
          </div>
        </article>
      </div>

      <p v-if="polling" class="polling-tip">有行程正在生成中，页面会自动刷新…</p>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, Calendar, MagicStick, Plus, RefreshRight } from '@element-plus/icons-vue'
import AppHeader from '../components/AppHeader.vue'
import request, { errorMessage } from '../api/request'
import { useUserStore } from '../stores/user'

interface TripSummary {
  trip_id: number
  destination: string
  status: string
  start_date: string | null
  end_date: string | null
  budget: number | null
  travelers: number | null
  day_count: number
  item_count: number
  total_cost: number
}

const router = useRouter()
const userStore = useUserStore()

const trips = ref<TripSummary[]>([])
const loading = ref(false)
const errorText = ref('')
let pollTimer: number | null = null

const polling = computed(() => trips.value.some(t => t.status === 'planning'))

const load = async (manual = false) => {
  if (manual) errorText.value = ''
  loading.value = true
  try {
    const res: any = await request.get('/api/v1/trips/mine')
    trips.value = res.trips || []
    errorText.value = ''
    schedulePolling()
  } catch (err) {
    errorText.value = errorMessage(err, '无法获取行程列表')
  } finally {
    loading.value = false
  }
}

const stopPolling = () => {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

// 有行程在生成中时，每 8 秒刷新一次，生成完自动更新状态
const schedulePolling = () => {
  stopPolling()
  if (!polling.value) return
  pollTimer = window.setInterval(() => load(), 8000)
}

const openTrip = (trip: TripSummary) => {
  router.push({ path: '/workbench', query: { trip_id: String(trip.trip_id) } })
}

const statusText = (status: string) => {
  if (status === 'ready') return '已生成'
  if (status === 'failed') return '生成失败'
  return '规划中'
}

const formatMoney = (value: number | null | undefined) =>
  Number(value || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })

const formatRange = (start: string | null, end: string | null) => {
  if (!start) return '未设置日期'
  const fmt = (d: string) => d.replaceAll('-', '.')
  return end && end !== start ? `${fmt(start)} — ${fmt(end)}` : fmt(start)
}

const budgetPercent = (trip: TripSummary) => {
  if (!trip.budget) return 0
  return Math.min(100, Math.round((Number(trip.total_cost || 0) / Number(trip.budget)) * 100))
}

// 根据目的地生成稳定的渐变配色，让卡片有辨识度
const PALETTE = [
  { gradient: 'linear-gradient(135deg, #0ea5e9, #0369a1)', emoji: '🏙️' },
  { gradient: 'linear-gradient(135deg, #f97316, #c2410c)', emoji: '🏜️' },
  { gradient: 'linear-gradient(135deg, #8b5cf6, #5b21b6)', emoji: '🏔️' },
  { gradient: 'linear-gradient(135deg, #10b981, #047857)', emoji: '🌿' },
  { gradient: 'linear-gradient(135deg, #06b6d4, #0e7490)', emoji: '🌊' },
  { gradient: 'linear-gradient(135deg, #ef4444, #991b1b)', emoji: '🏯' }
]

const themeCache = new Map<string, { gradient: string; emoji: string }>()
const themeOf = (destination: string) => {
  const key = destination || ''
  const cached = themeCache.get(key)
  if (cached) return cached
  let sum = 0
  for (let i = 0; i < key.length; i++) sum += key.charCodeAt(i)
  const theme = PALETTE[sum % PALETTE.length]
  themeCache.set(key, theme)
  return theme
}

onMounted(load)
onBeforeUnmount(stopPolling)
</script>

<style scoped>
.trips-page {
  min-height: 100vh;
  background: #f6f8fb;
  padding-bottom: 60px;
}

.container {
  max-width: 1140px;
  margin: 0 auto;
  padding: 36px 24px 0;
}

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
  margin-bottom: 26px;
}

.page-head h1 {
  margin: 0 0 8px;
  font-size: 28px;
  letter-spacing: 0.5px;
  color: #0f172a;
}

.page-head p {
  margin: 0;
  font-size: 14px;
  color: #64748b;
}

.page-head__actions {
  display: flex;
  gap: 10px;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 40px;
  padding: 0 16px;
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.18s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn--ghost {
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #475569;
}

.btn--ghost:hover:not(:disabled) {
  border-color: #0d9488;
  color: #0d9488;
}

.btn--primary {
  border: none;
  color: #fff;
  font-weight: 500;
  background: linear-gradient(135deg, #14b8a6, #0d9488);
  box-shadow: 0 8px 18px rgba(13, 148, 136, 0.24);
}

.btn--primary:hover:not(:disabled) {
  transform: translateY(-1px);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

/* ---------- 卡片 ---------- */
.trip-card {
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
}

.trip-card:hover {
  transform: translateY(-4px);
  border-color: #ccfbf1;
  box-shadow: 0 18px 34px rgba(15, 23, 42, 0.1);
}

.trip-card__cover {
  position: relative;
  height: 96px;
  display: flex;
  align-items: center;
  padding: 0 18px;
  overflow: hidden;
}

.trip-card__cover::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image: radial-gradient(rgba(255, 255, 255, 0.35) 1px, transparent 1px);
  background-size: 16px 16px;
  opacity: 0.35;
}

.trip-card__emoji {
  position: relative;
  z-index: 1;
  font-size: 34px;
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.18));
}

.trip-card__status {
  position: absolute;
  z-index: 1;
  right: 14px;
  top: 14px;
  padding: 3px 10px;
  font-size: 12px;
  border-radius: 999px;
  color: #fff;
  background: rgba(255, 255, 255, 0.22);
  border: 1px solid rgba(255, 255, 255, 0.4);
  backdrop-filter: blur(4px);
}

.trip-card__status.is-ready {
  background: rgba(16, 185, 129, 0.92);
  border-color: transparent;
}

.trip-card__status.is-planning {
  background: rgba(245, 158, 11, 0.94);
  border-color: transparent;
}

.trip-card__status.is-failed {
  background: rgba(239, 68, 68, 0.92);
  border-color: transparent;
}

.trip-card__no {
  position: absolute;
  z-index: 1;
  right: 16px;
  bottom: 10px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  letter-spacing: 1px;
}

.trip-card__body {
  padding: 16px 18px 18px;
}

.trip-card__title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.trip-card__title h3 {
  margin: 0;
  font-size: 17px;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trip-card__arrow {
  color: #cbd5e1;
  transition: transform 0.18s, color 0.18s;
}

.trip-card:hover .trip-card__arrow {
  color: #0d9488;
  transform: translateX(3px);
}

.trip-card__date {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 8px 0 14px;
  font-size: 13px;
  color: #64748b;
}

.trip-card__stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
  padding: 12px 0;
  border-top: 1px dashed #eef2f7;
  border-bottom: 1px dashed #eef2f7;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat__value {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.stat__label {
  font-size: 11px;
  color: #94a3b8;
}

.stat--cost .stat__value {
  color: #0d9488;
}

.trip-card__budget {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
}

.budget__bar {
  flex: 1;
  height: 6px;
  border-radius: 999px;
  background: #f1f5f9;
  overflow: hidden;
}

.budget__bar span {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #2dd4bf, #0d9488);
}

.budget__text {
  font-size: 11px;
  color: #94a3b8;
  white-space: nowrap;
}

/* ---------- 骨架 / 状态 ---------- */
.skeleton {
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 16px;
  padding-bottom: 18px;
  overflow: hidden;
}

.skeleton__cover,
.skeleton__line {
  background: linear-gradient(90deg, #f1f5f9 25%, #e9eef5 37%, #f1f5f9 63%);
  background-size: 400% 100%;
  animation: shimmer 1.4s ease infinite;
}

.skeleton__cover {
  height: 96px;
  margin-bottom: 18px;
}

.skeleton__line {
  height: 12px;
  margin: 10px 18px;
  border-radius: 6px;
}

.skeleton__line--lg {
  height: 16px;
  width: 55%;
}

.skeleton__line--sm {
  width: 40%;
}

@keyframes shimmer {
  0% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0 50%;
  }
}

.state {
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 20px;
  padding: 60px 24px;
  text-align: center;
}

.state__icon {
  font-size: 40px;
  margin-bottom: 10px;
}

.state h3 {
  margin: 0 0 8px;
  font-size: 18px;
  color: #0f172a;
}

.state p {
  margin: 0 0 22px;
  font-size: 14px;
  color: #64748b;
}

.polling-tip {
  margin-top: 24px;
  text-align: center;
  font-size: 13px;
  color: #f59e0b;
}

@media (max-width: 640px) {
  .container {
    padding: 24px 16px 0;
  }
  .page-head h1 {
    font-size: 23px;
  }
}
</style>
