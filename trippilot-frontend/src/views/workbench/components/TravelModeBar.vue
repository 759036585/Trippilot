<!-- src/views/workbench/components/TravelModeBar.vue -->
<!-- 打车 / 公交 / 步行 切换 -->
<template>
  <div class="mode-bar">
    <button
      v-for="option in TRAVEL_MODES"
      :key="option.key"
      class="mode-btn"
      :class="{ on: modelValue === option.key }"
      :title="option.desc"
      @click="emit('change', option.key)"
    >
      <span class="mode-btn__icon">{{ option.icon }}</span>
      {{ option.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { TRAVEL_MODES } from '../constants'
import type { TravelMode } from '../types'

defineProps<{ modelValue: TravelMode }>()

const emit = defineEmits<{ change: [mode: TravelMode] }>()
</script>

<style scoped>
.mode-bar {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  padding: 0 18px 12px;
}
.mode-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 32px;
  border-radius: 9px;
  border: 1px solid var(--line);
  background: #fff;
  font-family: inherit;
  font-size: 12px;
  color: var(--muted);
  cursor: pointer;
  transition: all 0.16s;
}
.mode-btn:hover {
  border-color: #99f6e4;
  color: var(--teal-dark);
}
.mode-btn.on {
  background: var(--teal-soft);
  border-color: #99f6e4;
  color: var(--teal-dark);
  font-weight: 600;
}
.mode-btn__icon {
  font-size: 13px;
  line-height: 1;
}
</style>
