<!-- src/views/CreateTrip.vue -->
<template>
  <div class="create-page">
    <AppHeader solid />

    <div class="create-container">
      <div class="form-card">
        <div class="form-card__head">
          <h2>创建你的旅程</h2>
          <p class="subtitle">填写出发地、目的地和日期，AI 帮你规划城际交通、酒店住宿、每日行程与分类预算</p>
        </div>

        <!-- 游客提示：登录后行程才会保存 -->
        <div v-if="!userStore.isLoggedIn" class="notice">
          <el-icon><InfoFilled /></el-icon>
          <span>当前为游客模式，生成的行程不会保存</span>
          <button type="button" @click="goLogin">登录后自动保存 →</button>
        </div>

        <!-- 表单区域 -->
        <el-form :model="formData" label-position="top">
          <!-- 出发地 / 目的地 -->
          <div class="route-fields">
            <el-form-item label="出发地">
              <el-input v-model.trim="formData.origin" placeholder="如：北京" />
            </el-form-item>
            <span class="route-arrow">→</span>
            <el-form-item label="目的地">
              <el-input v-model.trim="formData.destination" placeholder="如：成都" />
            </el-form-item>
          </div>

          <!-- 日期范围选择 -->
          <el-form-item label="出行日期">
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="出发日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
          </el-form-item>

          <!-- 出行人数 -->
          <el-form-item label="出行人数">
            <el-input-number v-model="formData.travelers" :min="1" :max="20" />
          </el-form-item>

          <!-- 住宿档次 -->
          <el-form-item label="住宿档次">
            <el-radio-group v-model="formData.hotel_level">
              <el-radio-button value="经济型">经济型</el-radio-button>
              <el-radio-button value="舒适型">舒适型</el-radio-button>
              <el-radio-button value="豪华型">豪华型</el-radio-button>
            </el-radio-group>
          </el-form-item>

          <!-- 预算 -->
          <el-form-item label="总预算金额 (元，含交通与住宿)">
            <el-input-number v-model="formData.budget" :min="500" :step="500" style="width: 100%" />
          </el-form-item>

          <!-- 偏好（多选框） -->
          <el-form-item label="旅行偏好 (多选)">
            <el-checkbox-group v-model="formData.preferences">
              <el-checkbox label="自然风景" name="pref" />
              <el-checkbox label="美食" name="pref" />
              <el-checkbox label="历史文化" name="pref" />
              <el-checkbox label="亲子" name="pref" />
              <el-checkbox label="购物" name="pref" />
              <el-checkbox label="休闲" name="pref" />
            </el-checkbox-group>
          </el-form-item>

          <!-- 提交按钮 -->
          <div class="submit-btn-wrapper">
            <el-button
              type="warning"
              size="large"
              class="submit-btn"
              :loading="isLoading"
              @click="submitForm"
            >
              {{ isLoading ? 'AI 正在生成...' : '生成我的行程' }}
            </el-button>
            <p class="submit-tip">生成后可在工作台查看交通方案、酒店、地图与分类预算</p>
          </div>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import request, { errorMessage } from '../api/request'
import { ElMessage } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'
import AppHeader from '../components/AppHeader.vue'
import { useUserStore } from '../stores/user'

// 路由实例
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 表单数据对象 (reactive 适合处理对象)
const formData = reactive({
  origin: '',
  destination: '',
  travelers: 2,
  hotel_level: '舒适型',
  budget: 5000,
  preferences: [] as string[]
})

// 日期范围单独处理，因为 el-date-picker 返回的是数组
const dateRange = ref<[string, string] | null>(null)
// 加载状态
const isLoading = ref(false)

// 页面加载时，检查是否有从首页传过来的目的地
onMounted(() => {
  if (route.query.destination) {
    formData.destination = route.query.destination as string
  }
})

const goLogin = () => {
  router.push({ path: '/login', query: { redirect: route.fullPath } })
}

// 提交表单函数
const submitForm = async () => {
  // 1. 基础校验
  if (!formData.origin || !formData.destination || !dateRange.value) {
    ElMessage.warning('请填写出发地、目的地和出行日期')
    return
  }
  if (formData.origin === formData.destination) {
    ElMessage.warning('出发地和目的地不能相同')
    return
  }

  isLoading.value = true

  try {
    // 2. 组装发给后端的数据
    const payload = {
      origin: formData.origin,
      destination: formData.destination,
      start_date: dateRange.value[0],
      end_date: dateRange.value[1],
      travelers: formData.travelers,
      budget: formData.budget,
      preferences: formData.preferences,
      hotel_level: formData.hotel_level
    }

    // 3. 调用后端接口
    const res: any = await request.post('/api/v1/trips', payload)

    ElMessage.success('提交成功，AI 正在为您规划...')

    setTimeout(() => {
      // 跳转到工作台，并带上 trip_id
      router.push({
        path: '/workbench',
        query: { trip_id: res.trip_id }
      })
    }, 1200)

  } catch (error) {
    console.error(error)
    ElMessage.error(errorMessage(error, '请求失败，请检查后端是否启动'))
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.create-page {
  min-height: 100vh;
  background: #f6f8fb;
}

.create-container {
  display: flex;
  justify-content: center;
  padding: 40px 16px 60px;
}

.form-card {
  background: white;
  padding: 36px 40px 40px;
  border-radius: 18px;
  border: 1px solid #eef2f7;
  width: 100%;
  max-width: 620px;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.07);
}

.form-card__head h2 {
  margin: 0 0 6px;
  font-size: 24px;
  color: #0f172a;
  letter-spacing: 0.5px;
}

.subtitle {
  margin: 0 0 26px;
  color: #64748b;
  font-size: 13.5px;
}

.notice {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 20px;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fde68a;
}

.notice button {
  margin-left: auto;
  border: none;
  background: none;
  padding: 0;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  color: #0d9488;
  cursor: pointer;
}

/* 出发地 → 目的地：并排显示，箭头夹在中间 */
.route-fields {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
.route-fields :deep(.el-form-item) {
  flex: 1;
  margin-bottom: 18px;
}
.route-arrow {
  margin-bottom: 28px;
  color: #94a3b8;
  font-size: 15px;
  line-height: 1;
}

.submit-btn-wrapper {
  text-align: center;
  margin-top: 26px;
}

.submit-btn {
  width: 100%;
  height: 46px;
  border-radius: 12px;
  background: linear-gradient(135deg, #14b8a6, #0d9488);
  border: none;
  font-size: 15.5px;
  font-weight: 500;
  box-shadow: 0 10px 24px rgba(13, 148, 136, 0.26);
}

.submit-btn:hover {
  background: linear-gradient(135deg, #14b8a6, #0d9488);
  opacity: 0.92;
}

.submit-tip {
  margin: 12px 0 0;
  font-size: 12px;
  color: #94a3b8;
}

@media (max-width: 640px) {
  .form-card {
    padding: 26px 20px 30px;
  }
  .notice button {
    margin-left: 0;
  }
  .route-fields {
    flex-direction: column;
    gap: 0;
  }
  .route-fields :deep(.el-form-item) {
    width: 100%;
  }
  .route-arrow {
    display: none;
  }
}
</style>