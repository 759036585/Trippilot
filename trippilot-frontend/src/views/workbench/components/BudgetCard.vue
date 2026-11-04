<!-- src/views/workbench/components/BudgetCard.vue -->
<!-- 右栏顶部：总花费 / 预算进度 / 每天花费 -->
<template>
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
      <span v-if="budget">剩余 ¥{{ fmtMoney(remaining) }}</span>
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
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { dayColor, dayCost, fmtMoney } from '../format'
import type { TripDay } from '../types'

const props = defineProps<{
  days: TripDay[]
  totalCost: number
  budget: number | null
  budgetPercent: number
  travelers: number
}>()

const remaining = computed(() => (props.budget ? props.budget - props.totalCost : 0))
</script>

<style scoped>
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
</style>
