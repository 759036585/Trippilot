<!-- src/views/create/DraftSummary.vue -->
<!-- 需求齐了以后，在对话流里插入一张确认卡 -->
<template>
  <section class="draft-card">
    <div class="draft-head">
      <span class="draft-check">✓</span>
      <div>
        <h4>行程需求已确认</h4>
        <p>看一下有没有要改的，直接告诉助手就行</p>
      </div>
    </div>

    <dl class="draft-rows">
      <div>
        <dt>路线</dt>
        <dd>{{ draft.origin }} → {{ draft.destination }}</dd>
      </div>
      <div>
        <dt>日期</dt>
        <dd>{{ dateText }}</dd>
      </div>
      <div>
        <dt>同行</dt>
        <dd>{{ draft.travelers }} 人</dd>
      </div>
      <div>
        <dt>预算</dt>
        <dd>{{ fmtMoney(draft.budget) }} <span class="muted">全部人合计</span></dd>
      </div>
      <div>
        <dt>住宿</dt>
        <dd>{{ draft.hotel_level }}</dd>
      </div>
    </dl>

    <div v-if="draft.preferences.length" class="draft-tags">
      <span v-for="tag in draft.preferences" :key="tag">{{ tag }}</span>
    </div>

    <button type="button" class="draft-btn" :disabled="submitting" @click="emit('confirm')">
      {{ submitting ? '正在提交…' : '开始生成行程' }}
    </button>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { fmtDateWithWeek, fmtMoney, tripDayCount } from './format'
import type { PlannerDraft } from './types'

const props = defineProps<{ draft: PlannerDraft; submitting?: boolean }>()

const emit = defineEmits<{ confirm: [] }>()

const dateText = computed(() => {
  const days = tripDayCount(props.draft.start_date, props.draft.end_date)
  return `${fmtDateWithWeek(props.draft.start_date)} — ${fmtDateWithWeek(props.draft.end_date)}（${days} 天）`
})
</script>

<style scoped>
.draft-card {
  background: linear-gradient(180deg, #f0fdfa, #ffffff 62%);
  border: 1px solid #ccfbf1;
  border-radius: 16px;
  padding: 16px 18px 16px;
  box-shadow: 0 12px 30px rgba(13, 148, 136, 0.08);
  animation: draft-in 0.28s ease;
}

@keyframes draft-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.draft-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.draft-check {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: linear-gradient(135deg, #14b8a6, #0d9488);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
}
.draft-head h4 {
  margin: 0;
  font-size: 14px;
  color: #0f172a;
}
.draft-head p {
  margin: 2px 0 0;
  font-size: 11.5px;
  color: #94a3b8;
}

.draft-rows {
  margin: 14px 0 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 18px;
}
.draft-rows div {
  display: flex;
  gap: 8px;
  font-size: 12.5px;
  line-height: 1.5;
}
.draft-rows dt {
  color: #94a3b8;
  flex: 0 0 30px;
}
.draft-rows dd {
  margin: 0;
  color: #0f172a;
  font-weight: 600;
}

@media (max-width: 560px) {
  .draft-rows {
    grid-template-columns: 1fr;
  }
}
.muted {
  color: #94a3b8;
  font-weight: 400;
  font-size: 11px;
}

.draft-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}
.draft-tags span {
  font-size: 11.5px;
  color: #0d9488;
  background: #e6fffb;
  border: 1px solid #ccfbf1;
  border-radius: 999px;
  padding: 3px 10px;
}

.draft-btn {
  width: 100%;
  margin-top: 16px;
  height: 40px;
  border: none;
  border-radius: 11px;
  background: linear-gradient(135deg, #14b8a6, #0d9488);
  color: #fff;
  font-family: inherit;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 10px 22px rgba(13, 148, 136, 0.24);
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.draft-btn:hover:not(:disabled) {
  opacity: 0.92;
  transform: translateY(-1px);
}
.draft-btn:disabled {
  cursor: default;
  opacity: 0.7;
}
</style>
