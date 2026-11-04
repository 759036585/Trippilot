<!-- src/App.vue -->
<template>
  <!-- 这里是路由出口，访问 / 就会渲染 Home.vue -->
  <router-view />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useUserStore } from './stores/user'

const userStore = useUserStore()

// token 过期 / 无效时，请求拦截器会派发事件，这里统一清空登录态
const handleUnauthorized = () => userStore.logout()

onMounted(() => {
  window.addEventListener('tp:unauthorized', handleUnauthorized)
  // 页面刷新后校验一次 token，顺便拿到最新的昵称
  userStore.refresh()
})
onUnmounted(() => window.removeEventListener('tp:unauthorized', handleUnauthorized))
</script>

<style>
/* 清除浏览器的默认内外边距 */
body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background-color: #f5f7fa; /* 浅灰色背景，类似 UI 图 */
}

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}
</style>
