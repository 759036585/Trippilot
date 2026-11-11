<!-- src/views/workbench/components/PlanSummaryCard.vue -->
<!-- 左侧顶部：城际交通方案（推荐 + 备选）和酒店住宿 -->
<template>
  <section class="plan-card">
    <!-- 城际交通 -->
    <div class="plan-block">
      <div class="plan-head">
        <span class="plan-label">城际交通</span>
        <span class="plan-route">
          {{ origin || '出发地' }} <i>→</i> {{ destination || '目的地' }}
        </span>
      </div>

      <div v-if="recommended" class="plan-option">
        <span class="plan-icon">{{ recommendedMeta.icon }}</span>
        <div class="plan-body">
          <div class="plan-name">{{ recommended.summary }}</div>
          <div class="plan-meta">
            <span class="plan-tag">{{ recommendedMeta.label }}</span>
            <span v-if="departArrive">{{ departArrive }}</span>
            <span>{{ fmtMinutes(recommended.duration_minutes) }}</span>
            <span class="plan-cost" v-if="Number(recommended.cost) > 0">
              ¥{{ fmtMoney(recommended.cost) }}
            </span>
          </div>
          <div class="plan-note" v-if="recommended.note">{{ recommended.note }}</div>
        </div>
      </div>
      <p v-else class="plan-empty">本次规划没有返回城际交通方案</p>

      <template v-if="alternatives.length">
        <button class="plan-toggle" type="button" @click="showAlternatives = !showAlternatives">
          {{ showAlternatives ? '收起备选方案' : `查看 ${alternatives.length} 个备选方案` }}
        </button>
        <ul class="plan-alts" v-show="showAlternatives">
          <li v-for="(alt, index) in alternatives" :key="index">
            <span class="plan-icon plan-icon--sm">{{ transportMeta(alt.mode).icon }}</span>
            <div class="plan-alt-body">
              <div class="alt-name">{{ alt.summary }}</div>
              <div class="plan-meta">
                <span class="plan-tag">{{ transportMeta(alt.mode).label }}</span>
                <span>{{ fmtMinutes(alt.duration_minutes) }}</span>
                <span class="plan-cost" v-if="Number(alt.cost) > 0">¥{{ fmtMoney(alt.cost) }}</span>
              </div>
              <div class="plan-note" v-if="alt.note">{{ alt.note }}</div>
            </div>
          </li>
        </ul>
      </template>
    </div>

    <!-- 住宿 -->
    <div class="plan-block plan-block--hotel" v-if="hotel">
      <div class="plan-head">
        <span class="plan-label">住宿</span>
        <span class="plan-route" v-if="hotel.nights">{{ hotel.nights }} 晚</span>
      </div>
      <div class="plan-option">
        <span class="plan-icon plan-icon--hotel">🏨</span>
        <div class="plan-body">
          <div class="plan-name">
            {{ hotel.name }}
            <span class="hotel-rating" v-if="hotel.rating">★ {{ hotel.rating }}</span>
          </div>
          <div class="plan-meta">
            <span v-if="Number(hotel.price_per_night) > 0">
              ¥{{ fmtMoney(hotel.price_per_night) }}/晚
            </span>
            <span v-if="hotel.rooms && hotel.rooms > 1">{{ hotel.rooms }} 间</span>
            <span class="plan-cost" v-if="Number(hotel.cost) > 0">¥{{ fmtMoney(hotel.cost) }}</span>
          </div>
          <div class="plan-note" v-if="hotel.address">{{ hotel.address }}</div>
          <div class="plan-note" v-if="hotel.note">{{ hotel.note }}</div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { fmtMinutes, fmtMoney, transportMeta } from '../format'
import type { TripHotel, TripTransport } from '../types'

const props = defineProps<{
  origin?: string | null
  destination?: string | null
  transport?: TripTransport | null
  hotel?: TripHotel | null
}>()

const showAlternatives = ref(false)

const recommended = computed(() => props.transport?.recommended ?? null)
const alternatives = computed(() => props.transport?.alternatives ?? [])
const recommendedMeta = computed(() => transportMeta(recommended.value?.mode))

const departArrive = computed(() => {
  const option = recommended.value
  if (!option?.departure_time || !option?.arrival_time) return ''
  return `${option.departure_time} → ${option.arrival_time}`
})
</script>

<style scoped>
.plan-card {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: linear-gradient(180deg, #f7fdfc, #ffffff);
  margin: 4px 0 12px;
  overflow: hidden;
}
.plan-block {
  padding: 12px 13px;
}
.plan-block + .plan-block {
  border-top: 1px dashed var(--line);
}
.plan-block--hotel {
  background: #fbfaff;
}
.plan-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 9px;
}
.plan-label {
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.6px;
  color: var(--teal-dark);
}
.plan-block--hotel .plan-label {
  color: #4338ca;
}
.plan-route {
  font-size: 11.5px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.plan-route i {
  font-style: normal;
  color: #94a3b8;
  margin: 0 2px;
}
.plan-option {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.plan-icon {
  flex: 0 0 32px;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  background: #ecfdf5;
}
.plan-icon--hotel {
  background: #eef2ff;
}
.plan-icon--sm {
  flex-basis: 24px;
  width: 24px;
  height: 24px;
  font-size: 13px;
  border-radius: 8px;
}
.plan-body {
  flex: 1;
  min-width: 0;
}
.plan-name {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.35;
  color: var(--ink);
  word-break: break-word;
}
.plan-meta {
  margin-top: 4px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px 8px;
  font-size: 11.5px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.plan-tag {
  background: var(--teal-soft);
  color: var(--teal-dark);
  border-radius: 5px;
  padding: 1px 6px;
  font-size: 10.5px;
}
.plan-block--hotel .plan-tag {
  background: #eef2ff;
  color: #4338ca;
}
.plan-cost {
  margin-left: auto;
  color: var(--orange);
  font-weight: 600;
}
.plan-note {
  margin-top: 4px;
  font-size: 11px;
  color: #94a3b8;
  line-height: 1.4;
}
.hotel-rating {
  margin-left: 4px;
  font-size: 11px;
  color: #f59e0b;
  font-weight: 500;
}
.plan-empty {
  margin: 0;
  font-size: 11.5px;
  color: #94a3b8;
}
.plan-toggle {
  margin-top: 9px;
  border: none;
  background: none;
  padding: 0;
  font-family: inherit;
  font-size: 11.5px;
  color: var(--teal-dark);
  cursor: pointer;
}
.plan-toggle:hover {
  text-decoration: underline;
}
.plan-alts {
  list-style: none;
  margin: 8px 0 0;
  padding: 8px 0 0;
  border-top: 1px dashed var(--line);
  display: grid;
  gap: 9px;
}
.plan-alts li {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.plan-alt-body {
  flex: 1;
  min-width: 0;
}
.alt-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--ink);
}
</style>
