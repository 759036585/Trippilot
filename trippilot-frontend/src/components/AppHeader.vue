<!-- src/components/AppHeader.vue 通用顶部导航 -->
<template>
  <header class="app-header" :class="{ 'is-solid': solid }">
    <div class="app-header__inner">
      <!-- 品牌 -->
      <a class="brand" href="javascript:void(0)" @click="goHome">
        <span class="brand__mark">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
            <path d="M2.5 13.5 21 6.5l-4.2 5.2L21 17l-8.6-2.2L8 20l-1.4-4.9-4.1-1.6Z"
                  stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
          </svg>
        </span>
        <span class="brand__name">旅程 AI</span>
      </a>

      <!-- 主导航 -->
      <nav class="nav">
        <a class="nav__link" href="javascript:void(0)" @click="goDiscover">发现目的地</a>
        <a class="nav__link" href="javascript:void(0)" @click="goTrips">我的行程</a>
      </nav>

      <!-- 右侧操作区 -->
      <div class="actions">
        <el-dropdown v-if="userStore.isLoggedIn" trigger="click" @command="onCommand">
          <button class="user-chip" type="button">
            <span class="user-chip__avatar">{{ userStore.initial }}</span>
            <span class="user-chip__name">{{ userStore.displayName }}</span>
            <el-icon class="user-chip__caret"><ArrowDown /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="trips">
                <el-icon><Clock /></el-icon>我的行程
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided>
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <template v-else>
          <button class="ghost-btn" type="button" @click="goLogin">登录</button>
          <button class="primary-btn" type="button" @click="goCreate">开始规划</button>
        </template>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowDown, Clock, SwitchButton } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user'

defineProps<{ solid?: boolean }>()

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const goHome = () => {
  if (route.path === '/') {
    window.scrollTo({ top: 0, behavior: 'smooth' })
    return
  }
  router.push('/')
}

const goCreate = () => router.push('/create')

const goDiscover = () => {
  const scroll = () => document.getElementById('discover')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  if (route.path === '/') {
    scroll()
  } else {
    router.push('/').then(() => window.setTimeout(scroll, 120))
  }
}

const goTrips = () => {
  if (!userStore.isLoggedIn) {
    ElMessage.info('登录后即可查看你的行程历史')
  }
  router.push('/trips')
}

const goLogin = () => {
  router.push({ path: '/login', query: { redirect: route.fullPath } })
}

const onCommand = (command: string) => {
  if (command === 'trips') {
    router.push('/trips')
  } else if (command === 'logout') {
    userStore.logout()
    ElMessage.success('已退出登录')
    if (route.meta.requiresAuth) router.push('/')
  }
}
</script>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: saturate(180%) blur(14px);
  -webkit-backdrop-filter: saturate(180%) blur(14px);
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.app-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  height: 64px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  gap: 32px;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  cursor: pointer;
  flex-shrink: 0;
}

.brand__mark {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  color: #fff;
  background: linear-gradient(135deg, #14b8a6, #0d9488);
  box-shadow: 0 4px 12px rgba(13, 148, 136, 0.32);
}

.brand__name {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: #0f172a;
}

.nav {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
}

.nav__link {
  position: relative;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 14px;
  color: #475569;
  text-decoration: none;
  cursor: pointer;
  transition: color 0.18s, background-color 0.18s;
}

.nav__link:hover {
  color: #0d9488;
  background: rgba(13, 148, 136, 0.08);
}

.actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ghost-btn,
.primary-btn {
  height: 38px;
  padding: 0 18px;
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.18s;
}

.ghost-btn {
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #334155;
}

.ghost-btn:hover {
  border-color: #0d9488;
  color: #0d9488;
}

.primary-btn {
  border: none;
  color: #fff;
  font-weight: 500;
  background: linear-gradient(135deg, #14b8a6, #0d9488);
  box-shadow: 0 6px 16px rgba(13, 148, 136, 0.26);
}

.primary-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(13, 148, 136, 0.34);
}

.user-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 38px;
  padding: 0 12px 0 6px;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #fff;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.18s;
}

.user-chip:hover {
  border-color: #99f6e4;
  background: #f0fdfa;
}

.user-chip__avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #2dd4bf, #0d9488);
}

.user-chip__name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  color: #1e293b;
}

.user-chip__caret {
  color: #94a3b8;
  font-size: 12px;
}

@media (max-width: 768px) {
  .app-header__inner {
    padding: 0 14px;
    gap: 12px;
  }
  .nav {
    gap: 0;
  }
  .nav__link {
    padding: 8px;
    font-size: 13px;
  }
  .ghost-btn {
    display: none;
  }
  .user-chip__name {
    display: none;
  }
}
</style>
