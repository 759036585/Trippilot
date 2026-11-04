<!-- src/views/workbench/components/MapPanel.vue -->
<!-- 中间地图：容器 + 天筛选 + 查看全部 + 加载失败提示 -->
<template>
  <div class="center-panel">
    <div id="amap-container"></div>

    <!-- 天筛选 -->
    <div class="map-toolbar" v-if="!mapError">
      <button class="map-chip" :class="{ on: mapDay === 0 }" @click="emit('select-day', 0)">全部</button>
      <button
        v-for="day in days"
        :key="day.day_index"
        class="map-chip"
        :class="{ on: mapDay === day.day_index }"
        :style="{ '--c': dayColor(day.day_index - 1) }"
        @click="emit('select-day', day.day_index)"
      >第{{ day.day_index }}天</button>
    </div>

    <button class="map-fab" v-if="!mapError" title="查看全部地点" @click="emit('fit-all', true)">
      <el-icon><FullScreen /></el-icon>
    </button>

    <div v-if="mapError" class="map-error">
      <div class="map-error__card">
        <span class="map-error__icon">🗺️</span>
        <p>{{ mapError }}</p>
        <el-button size="small" @click="emit('retry')">重试</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { FullScreen } from '@element-plus/icons-vue'
import { dayColor } from '../format'
import type { TripDay } from '../types'

defineProps<{
  days: TripDay[]
  mapDay: number
  mapError: string
}>()

const emit = defineEmits<{
  'select-day': [dayIndex: number]
  'fit-all': [animate: boolean]
  retry: []
}>()
</script>

<style scoped>
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
</style>

<!-- 地图标记 / 信息窗体是注入到地图容器里的，不受 scoped 约束，所以放在全局样式里 -->
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
