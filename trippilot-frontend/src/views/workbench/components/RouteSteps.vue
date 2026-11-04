<!-- src/views/workbench/components/RouteSteps.vue -->
<!-- 展开后的换乘 / 途经详情 -->
<template>
  <div class="route-steps">
    <div v-for="(step, stepIndex) in steps" :key="stepIndex" class="route-steps__item">
      <span class="route-steps__icon" :class="`is-${step.mode}`">{{ stepIcon(step) }}</span>
      <div class="route-steps__body">
        <p class="route-steps__title">{{ stepTitle(step) }}</p>
        <p class="route-steps__meta" v-if="stepMeta(step)">{{ stepMeta(step) }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { fmtDist, fmtDur } from '../format'
import type { RouteStep } from '../types'

defineProps<{ steps: RouteStep[] }>()

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
</script>

<style scoped>
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
</style>
