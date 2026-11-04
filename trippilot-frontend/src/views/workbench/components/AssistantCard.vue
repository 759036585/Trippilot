<!-- src/views/workbench/components/AssistantCard.vue -->
<!-- 右栏底部：用一句话让 AI 调整行程 -->
<template>
  <section class="assistant-card">
    <div class="assistant-head">
      <span class="assistant-avatar">AI</span>
      <div>
        <h4>AI 助手</h4>
        <p class="nearby-sub">说一句话就能调整行程</p>
      </div>
    </div>
    <el-input
      v-model="chatInput"
      type="textarea"
      :rows="2"
      resize="none"
      placeholder="比如：把第二天的景点换成室内的"
    />
    <el-button type="primary" class="assistant-btn" :loading="revising" @click="sendRevision">
      发送修改指令
    </el-button>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../../../api/request'

const props = defineProps<{ tripId?: string | number | null }>()

const chatInput = ref('')
const revising = ref(false)

async function sendRevision() {
  if (!chatInput.value.trim()) {
    ElMessage.warning('先说说你想怎么调整吧')
    return
  }
  if (!props.tripId) {
    ElMessage.warning('缺少行程信息，请重新进入工作台')
    return
  }
  revising.value = true
  try {
    await request.post(`/api/v1/trips/${props.tripId}/revisions`, {
      instruction: chatInput.value.trim()
    })
    ElMessage.success('修改指令已发送，正在重新规划…')
    chatInput.value = ''
  } catch (error) {
    console.error('修改失败', error)
    ElMessage.error('发送失败，请稍后再试')
  } finally {
    revising.value = false
  }
}
</script>

<style scoped>
.assistant-card {
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 0 0 auto;
  background: linear-gradient(180deg, #fbfdfd, #ffffff);
}
.assistant-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.assistant-head h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
}
.nearby-sub {
  margin: 3px 0 0;
  font-size: 11.5px;
  color: var(--muted);
  max-width: 230px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.assistant-avatar {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.assistant-btn {
  width: 100%;
  border-radius: 10px;
}
:deep(.el-textarea__inner) {
  border-radius: 10px;
  font-size: 12.5px;
  box-shadow: 0 0 0 1px var(--line) inset;
}
:deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 1px var(--teal) inset;
}
</style>
