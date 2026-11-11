<!-- src/views/workbench/components/BudgetCard.vue -->
<!-- 右栏顶部：总花费 / 预算进度 / 分类花费明细 -->
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

    <ul class="breakdown" v-if="rows.length">
      <li v-for="row in rows" :key="row.key">
        <span class="bd-icon">{{ row.icon }}</span>
        <span class="bd-label">{{ row.label }}</span>
        <span class="bd-bar">
          <i :style="{ width: row.percent + '%', background: row.color }"></i>
        </span>
        <span class="bd-value">¥{{ fmtMoney(row.value) }}</span>
      </li>
    </ul>
    <p class="breakdown-empty" v-else>暂无分类花费</p>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { fmtMoney } from '../format'
import type { BudgetBreakdown } from '../types'

const props = defineProps<{
  breakdown: BudgetBreakdown | null
  totalCost: number
  budget: number | null
  budgetPercent: number
  travelers: number
}>()

const remaining = computed(() => (props.budget ? props.budget - props.totalCost : 0))

type BreakdownKey = Exclude<keyof BudgetBreakdown, 'total'>

const BUDGET_ROWS: { key: BreakdownKey; label: string; icon: string; color: string }[] = [
  { key: 'transport', label: '城际交通', icon: '🚄', color: '#38bdf8' },
  { key: 'local_transport', label: '市内交通', icon: '🚕', color: '#22d3ee' },
  { key: 'accommodation', label: '住宿', icon: '🏨', color: '#a78bfa' },
  { key: 'food', label: '餐饮', icon: '🍜', color: '#fb923c' },
  { key: 'tickets', label: '门票玩乐', icon: '🎫', color: '#34d399' },
  { key: 'shopping', label: '购物', icon: '🛍', color: '#f472b6' },
  { key: 'other', label: '其他', icon: '📦', color: '#cbd5e1' }
]

const rows = computed(() => {
  const breakdown = props.breakdown
  if (!breakdown) return []
  const total = Number(breakdown.total) || 0
  return BUDGET_ROWS.map((row) => {
    const value = Number(breakdown[row.key]) || 0
    return {
      ...row,
      value,
      percent: total > 0 ? Math.max(2, Math.round((value / total) * 100)) : 0
    }
  }).filter((row) => row.value > 0)
})
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
.breakdown {
  list-style: none;
  margin: 14px 0 0;
  padding: 12px 0 0;
  border-top: 1px solid rgba(255, 255, 255, 0.18);
  display: grid;
  gap: 7px;
}
.breakdown li {
  display: grid;
  grid-template-columns: 16px 52px 1fr auto;
  align-items: center;
  gap: 7px;
  font-size: 11.5px;
}
.bd-icon {
  font-size: 12px;
  line-height: 1;
}
.bd-label {
  opacity: 0.9;
}
.bd-bar {
  height: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  overflow: hidden;
}
.bd-bar i {
  display: block;
  height: 100%;
  border-radius: 999px;
  transition: width 0.5s ease;
}
.bd-value {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.breakdown-empty {
  margin: 12px 0 0;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.18);
  font-size: 11.5px;
  opacity: 0.75;
}
</style>
