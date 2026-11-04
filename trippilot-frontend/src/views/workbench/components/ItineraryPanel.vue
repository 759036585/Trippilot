<!-- src/views/workbench/components/ItineraryPanel.vue -->
<!-- 左侧行程面板：标题、出行方式、按天折叠的行程列表 -->
<template>
  <aside class="left-panel">
    <div class="panel-head">
      <div>
        <h3>行程安排</h3>
        <p class="panel-sub">{{ days.length }} 天 · {{ stopCount }} 个地点 · 预计 ¥{{ fmtMoney(totalCost) }}</p>
      </div>
      <button class="mini-btn" v-if="hasCollapsed" @click="expandAll">展开全部</button>
    </div>

    <TravelModeBar :model-value="travelMode" @change="emit('switch-mode', $event)" />

    <div class="panel-scroll">
      <DaySection
        v-for="day in days"
        :key="day.day_index"
        :day="day"
        :color="dayColor(day.day_index - 1)"
        :collapsed="isCollapsed(day.day_index)"
        :active-item-id="activeItemId"
        :routes="routes"
        :routes-loading="routesLoading"
        :travel-mode="travelMode"
        :travel-mode-label="travelModeLabel"
        :travel-mode-icon="travelModeIcon"
        :expanded-segment="expandedSegment"
        :summary="daySummary[day.day_index]"
        :segment-of="segmentOf"
        :register-item-el="setItemRef"
        @toggle="toggleDay(day.day_index)"
        @select="(item) => emit('select', item, day)"
        @toggle-segment="(dayIndex, index) => emit('toggle-segment', dayIndex, index)"
      />
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { dayColor, fmtMoney } from '../format'
import type {
  DayRouteSummary,
  RouteInfo,
  TravelMode,
  TripDay,
  TripItem
} from '../types'
import DaySection from './DaySection.vue'
import TravelModeBar from './TravelModeBar.vue'

defineProps<{
  days: TripDay[]
  stopCount: number
  totalCost: number
  travelMode: TravelMode
  travelModeLabel: string
  travelModeIcon: string
  daySummary: Record<number, DayRouteSummary>
  routes: Record<string, RouteInfo>
  routesLoading: boolean
  activeItemId?: number | null
  expandedSegment: string
  segmentOf: (dayIndex: number, index: number) => RouteInfo | undefined
}>()

const emit = defineEmits<{
  select: [item: TripItem, day: TripDay]
  'switch-mode': [mode: TravelMode]
  'toggle-segment': [dayIndex: number, index: number]
}>()

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

// ---------- 选中地点后的自动滚动 ----------
const itemEls = new Map<number, Element>()

function setItemRef(id: number, el: unknown) {
  if (el instanceof Element) itemEls.set(id, el)
  else itemEls.delete(id)
}

/** 展开对应的一天，并把地点卡片滚到可视区域 */
async function revealItem(dayIndex: number, itemId: number) {
  if (isCollapsed(dayIndex)) {
    collapsedDays.value = collapsedDays.value.filter((i) => i !== dayIndex)
    await nextTick()
  }
  itemEls.get(itemId)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
}

defineExpose({ revealItem })
</script>

<style scoped>
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
.panel-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px 24px;
  scrollbar-width: thin;
}
.panel-scroll::-webkit-scrollbar {
  width: 6px;
}
.panel-scroll::-webkit-scrollbar-thumb {
  background: #dbe4e9;
  border-radius: 3px;
}

@media (max-width: 1440px) {
  .left-panel {
    width: 320px;
    flex-basis: 320px;
  }
}
@media (max-width: 1180px) {
  .left-panel {
    width: 288px;
    flex-basis: 288px;
  }
}
</style>
