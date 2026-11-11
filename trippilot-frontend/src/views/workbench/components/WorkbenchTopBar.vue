<!-- src/views/workbench/components/WorkbenchTopBar.vue -->
<template>
  <header class="top-bar">
    <div class="brand">
      <div class="brand-mark">✈</div>
      <div class="brand-text">
        <span class="brand-name">旅程 AI</span>
        <span class="brand-sub">行程工作台</span>
      </div>
    </div>

    <div class="trip-meta" v-if="ready && destination">
      <span class="pill pill--dest">
        <template v-if="origin">{{ origin }}<i class="route-arrow">→</i></template>{{ destination }}
      </span>
      <span class="pill">{{ dayCount }} 天 · {{ stopCount }} 个地点</span>
      <span class="pill" v-if="dateRange">{{ dateRange }}</span>
      <span class="badge-done">已生成</span>
    </div>

    <button class="ghost-btn" @click="emit('home')">
      <el-icon><RefreshRight /></el-icon>
      重新规划
    </button>
  </header>
</template>

<script setup lang="ts">
import { RefreshRight } from '@element-plus/icons-vue'

defineProps<{
  ready: boolean
  origin?: string
  destination?: string
  dayCount: number
  stopCount: number
  dateRange: string
}>()

const emit = defineEmits<{ home: [] }>()
</script>

<style scoped>
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
.route-arrow {
  font-style: normal;
  color: #94a3b8;
  margin: 0 4px;
  font-weight: 400;
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

@media (max-width: 1180px) {
  .trip-meta .pill:nth-child(3) {
    display: none;
  }
}
</style>
