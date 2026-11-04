<!-- src/views/workbench/components/RouteChip.vue -->
<!-- 两个地点之间的路段条：有没有数据、估算还是真实路线、能不能展开详情 -->
<template>
  <button
    class="route-chip"
    type="button"
    :class="{ clickable: stepCount > 0 }"
    @click.stop="emit('toggle')"
  >
    <template v-if="segment">
      <span class="route-chip__icon" :class="`is-${mode}`">{{ modeIcon }}</span>
      <span class="route-chip__body">
        <span class="route-chip__title">
          {{ lineTitle || modeLabel }}
          <em v-if="segment.estimated">估算</em>
        </span>
        <span class="route-chip__meta">
          约 {{ fmtDur(segment.duration) }} ·
          {{ fmtDist(segment.distance) }}
          <span v-if="segment.cost" class="route-cost">· ¥{{ fmtMoney(segment.cost) }}</span>
        </span>
      </span>
      <span v-if="stepCount" class="route-more">{{ expanded ? '收起' : '详情' }}</span>
    </template>

    <template v-else-if="loading">
      <span class="route-chip__icon loading">···</span>
      <span class="route-chip__body">
        <span class="route-chip__title">正在计算{{ modeLabel }}路线…</span>
      </span>
    </template>

    <template v-else>
      <span class="route-chip__icon">—</span>
      <span class="route-chip__body">
        <span class="route-chip__title">
          {{ mode === 'transit' ? '暂无公交换乘方案' : '暂无路线数据' }}
        </span>
      </span>
    </template>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { fmtDist, fmtDur, fmtMoney } from '../format'
import type { RouteInfo, TravelMode } from '../types'

const props = defineProps<{
  segment?: RouteInfo
  loading: boolean
  mode: TravelMode
  modeLabel: string
  modeIcon: string
  stepCount: number
  expanded: boolean
}>()

const emit = defineEmits<{ toggle: [] }>()

/** 公交模式下把线路名拼出来，比如「地铁4号线 → 113路」 */
const lineTitle = computed(() => {
  const lines = (props.segment?.steps ?? [])
    .filter((step) => step.line)
    .map((step) => step.line as string)
  return [...new Set(lines)].join(' → ')
})
</script>

<style scoped>
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
</style>
