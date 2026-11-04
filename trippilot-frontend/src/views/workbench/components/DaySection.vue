<!-- src/views/workbench/components/DaySection.vue -->
<!-- 左侧某一天的折叠卡片：日期头 + 时间线 + 每个地点 + 路段 -->
<template>
  <section class="day-section" :class="{ collapsed }">
    <button class="day-head" @click="emit('toggle')">
      <span class="day-badge" :style="{ background: color }">
        {{ day.day_index }}
      </span>
      <span class="day-titles">
        <span class="day-title">第 {{ day.day_index }} 天</span>
        <span class="day-sub">{{ fmtDate(day.date) }} · {{ weekday(day.date) }}</span>
      </span>
      <span class="day-cost">¥{{ fmtMoney(dayCost(day)) }}</span>
      <span class="chevron">›</span>
    </button>

    <div class="day-body" v-show="!collapsed">
      <div class="day-route-summary" v-if="summary">
        <span class="route-line-icon"></span>
        全程 {{ fmtDist(summary.distance) }} · 约 {{ fmtDur(summary.duration) }}
      </div>

      <div class="timeline">
        <div v-for="(item, index) in day.items" :key="item.id" class="tl-node">
          <div class="rail">
            <span
              class="rail-dot"
              :class="{ active: isActive(item) }"
              :style="{ '--c': color }"
            >{{ index + 1 }}</span>
            <span class="rail-line" v-if="index < day.items.length - 1"></span>
          </div>

          <div class="node-body">
            <div
              class="place-card"
              :class="{ active: isActive(item) }"
              :ref="(el) => registerItemEl(item.id, el)"
              @click="emit('select', item)"
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

            <RouteChip
              v-if="index < day.items.length - 1"
              :segment="segmentOf(day.day_index, index)"
              :loading="routesLoading"
              :mode="travelMode"
              :mode-label="travelModeLabel"
              :mode-icon="travelModeIcon"
              :step-count="stepsOf(index).length"
              :expanded="expandedSegment === segmentKey(day.day_index, index)"
              @toggle="emit('toggle-segment', day.day_index, index)"
            />

            <RouteSteps
              v-if="expandedSegment === segmentKey(day.day_index, index) && stepsOf(index).length"
              :steps="stepsOf(index)"
            />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Clock, Ticket } from '@element-plus/icons-vue'
import { dayCost, fmtDate, fmtDist, fmtDur, fmtMoney, segmentKey, weekday } from '../format'
import type { DayRouteSummary, RouteInfo, TravelMode, TripDay, TripItem } from '../types'
import RouteChip from './RouteChip.vue'
import RouteSteps from './RouteSteps.vue'

const props = defineProps<{
  day: TripDay
  color: string
  collapsed: boolean
  activeItemId?: number | null
  routes: Record<string, RouteInfo>
  routesLoading: boolean
  travelMode: TravelMode
  travelModeLabel: string
  travelModeIcon: string
  expandedSegment: string
  summary?: DayRouteSummary
  segmentOf: (dayIndex: number, index: number) => RouteInfo | undefined
  /** 让父级记下地点卡片的 DOM，用于自动滚动 */
  registerItemEl: (id: number, el: unknown) => void
}>()

const emit = defineEmits<{
  toggle: []
  select: [item: TripItem]
  'toggle-segment': [dayIndex: number, index: number]
}>()

function isActive(item: TripItem) {
  return props.activeItemId === item.id
}

function stepsOf(index: number) {
  return props.routes[segmentKey(props.day.day_index, index)]?.steps ?? []
}
</script>

<style scoped>
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
</style>
