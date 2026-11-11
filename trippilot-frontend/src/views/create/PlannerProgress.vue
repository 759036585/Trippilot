<!-- src/views/create/PlannerProgress.vue -->
<!-- 右栏：对话中实时收集到的行程需求，缺失项标灰 -->
<template>
  <section class="progress-card">
    <div class="progress-head">
      <div>
        <h3>行程需求</h3>
        <p class="progress-sub">助手正在帮你一点点补齐</p>
      </div>
      <span class="progress-count">{{ filled }}/{{ REQUIRED_COUNT }}</span>
    </div>

    <div class="progress-bar">
      <i :style="{ width: percent + '%' }"></i>
    </div>

    <ul class="rows">
      <li v-for="row in rows" :key="row.key" :class="{ 'is-empty': !row.value }">
        <span class="row-icon">{{ row.icon }}</span>
        <span class="row-label">{{ row.label }}</span>
        <span class="row-value">{{ row.value || '待确认' }}</span>
      </li>
    </ul>

    <button v-if="ready" type="button" class="confirm-btn" :disabled="submitting" @click="emit('confirm')">
      {{ submitting ? '正在提交…' : '开始生成行程' }}
      <span v-if="!submitting" class="arrow">→</span>
    </button>
    <p v-else class="progress-tip">
      {{ missing.length ? `还差 ${missing.length} 项信息，继续聊就行` : '马上就好' }}
    </p>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { fmtDateWithWeek, fmtMoney, tripDayCount } from './format'
import type { MissingField, PlannerDraft } from './types'

const props = defineProps<{
  draft: PlannerDraft
  missing: MissingField[]
  ready: boolean
  submitting?: boolean
}>()

const emit = defineEmits<{ confirm: [] }>()

const REQUIRED_COUNT = 6

const filled = computed(() => REQUIRED_COUNT - props.missing.length)
const percent = computed(() => Math.round((filled.value / REQUIRED_COUNT) * 100))

const routeText = computed(() => {
  const { origin, destination } = props.draft
  if (origin && destination) return `${origin} → ${destination}`
  if (destination) return `去 ${destination}`
  if (origin) return `从 ${origin} 出发`
  return ''
})

const dateText = computed(() => {
  const { start_date: start, end_date: end } = props.draft
  if (!start || !end) return ''
  const days = tripDayCount(start, end)
  return `${fmtDateWithWeek(start)} 出发 · ${days} 天`
})

const rows = computed(() => [
  { key: 'route', icon: '📍', label: '路线', value: routeText.value },
  { key: 'dates', icon: '🗓', label: '日期', value: dateText.value },
  {
    key: 'travelers',
    icon: '👥',
    label: '人数',
    value: props.draft.travelers ? `${props.draft.travelers} 人` : ''
  },
  { key: 'budget', icon: '💰', label: '预算', value: fmtMoney(props.draft.budget) },
  { key: 'hotel', icon: '🏨', label: '住宿', value: props.draft.hotel_level },
  {
    key: 'preferences',
    icon: '🎯',
    label: '偏好',
    value: props.draft.preferences.length ? props.draft.preferences.join(' · ') : ''
  }
])
</script>

<style scoped>
.progress-card {
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 16px;
  padding: 18px 18px 16px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
}

.progress-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
.progress-head h3 {
  margin: 0;
  font-size: 15px;
  color: #0f172a;
  letter-spacing: 0.3px;
}
.progress-sub {
  margin: 4px 0 0;
  font-size: 11.5px;
  color: #94a3b8;
}
.progress-count {
  font-size: 12px;
  font-weight: 700;
  color: #0d9488;
  background: #e6fffb;
  border-radius: 999px;
  padding: 3px 9px;
  flex: 0 0 auto;
}

.progress-bar {
  height: 5px;
  border-radius: 999px;
  background: #eef2f7;
  margin: 14px 0 16px;
  overflow: hidden;
}
.progress-bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #14b8a6, #0d9488);
  transition: width 0.35s ease;
}

.rows {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.rows li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 0;
  border-bottom: 1px dashed #f1f5f9;
  font-size: 12.5px;
  color: #334155;
}
.rows li:last-child {
  border-bottom: none;
}
.row-icon {
  width: 20px;
  text-align: center;
  font-size: 13px;
  flex: 0 0 auto;
}
.row-label {
  color: #94a3b8;
  flex: 0 0 34px;
}
.row-value {
  margin-left: auto;
  text-align: right;
  font-weight: 600;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rows li.is-empty .row-value {
  color: #cbd5e1;
  font-weight: 500;
}

.confirm-btn {
  width: 100%;
  margin-top: 16px;
  height: 40px;
  border: none;
  border-radius: 11px;
  background: linear-gradient(135deg, #14b8a6, #0d9488);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  box-shadow: 0 10px 22px rgba(13, 148, 136, 0.24);
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.confirm-btn:hover:not(:disabled) {
  opacity: 0.92;
  transform: translateY(-1px);
}
.confirm-btn:disabled {
  cursor: default;
  opacity: 0.7;
}
.arrow {
  margin-left: 4px;
}

.progress-tip {
  margin: 16px 0 0;
  font-size: 11.5px;
  color: #94a3b8;
  text-align: center;
}
</style>
