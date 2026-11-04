<!-- src/views/workbench/components/WorkbenchState.vue -->
<!-- 规划中 / 失败 / 缺少参数 三种整页状态 -->
<template>
  <div class="state-page">
    <div v-if="status === 'planning'" class="planning-card">
      <div class="orbit">
        <span class="orbit-ring"></span>
        <span class="orbit-plane">✈</span>
      </div>
      <h3>AI 正在为你精心规划行程</h3>
      <p>正在查询真实景点、计算交通耗时并安排每日路线，请稍候…</p>
      <div class="skeleton-lines">
        <i style="width: 78%"></i>
        <i style="width: 60%"></i>
        <i style="width: 68%"></i>
      </div>
    </div>

    <el-result
      v-else-if="status === 'failed'"
      icon="error"
      title="规划失败"
      sub-title="AI 规划行程时出错了，请返回重新提交一次。"
    >
      <template #extra>
        <el-button type="primary" @click="emit('home')">返回重新规划</el-button>
      </template>
    </el-result>

    <el-result
      v-else
      icon="warning"
      title="缺少行程参数"
      sub-title="地址中没有 trip_id，请重新提交规划需求。"
    >
      <template #extra>
        <el-button type="primary" @click="emit('home')">返回重新规划</el-button>
      </template>
    </el-result>
  </div>
</template>

<script setup lang="ts">
import type { PageStatus } from '../types'

defineProps<{ status: PageStatus }>()

const emit = defineEmits<{ home: [] }>()
</script>

<style scoped>
.state-page {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.planning-card {
  width: 460px;
  max-width: 92vw;
  background: #fff;
  border-radius: 20px;
  padding: 40px 36px 32px;
  text-align: center;
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
}
.planning-card h3 {
  margin: 22px 0 8px;
  font-size: 17px;
}
.planning-card p {
  margin: 0;
  font-size: 13px;
  color: var(--muted);
  line-height: 1.7;
}
.orbit {
  position: relative;
  width: 84px;
  height: 84px;
  margin: 0 auto;
}
.orbit-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px dashed #b8e6df;
  animation: spin 6s linear infinite;
}
.orbit-plane {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  animation: float 2.4s ease-in-out infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@keyframes float {
  0%,
  100% {
    transform: translateY(-3px);
  }
  50% {
    transform: translateY(3px);
  }
}
.skeleton-lines {
  margin-top: 22px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: center;
}
.skeleton-lines i {
  display: block;
  height: 8px;
  border-radius: 999px;
  background: linear-gradient(90deg, #eef2f5, #e2e8ee, #eef2f5);
  background-size: 200% 100%;
  animation: shimmer 1.6s linear infinite;
}
@keyframes shimmer {
  to {
    background-position: -200% 0;
  }
}
</style>
