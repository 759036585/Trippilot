// src/router/index.ts
import { createRouter, createWebHistory, type RouteComponent, type RouteRecordRaw } from 'vue-router'
import { useUserStore } from '../stores/user'

/**
 * 懒加载封装：加载失败时（通常是部署新版本导致旧 chunk 失效）自动刷新页面
 * 以获取最新资源，避免白屏卡死。
 */
const lazyLoad = (view: () => Promise<RouteComponent>): RouteComponent => {
  return () =>
    view().catch((err) => {
      // 避免无限刷新：仅在未标记过刷新时执行
      if (!window.location.hash.includes('reload=1')) {
        window.location.reload()
      }
      throw err
    })
}

// 定义路由规则
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    // 懒加载：只有访问这个页面时，才去下载对应的代码，加快首屏速度
    component: lazyLoad(() => import('../views/Home.vue'))
  },
  {
    path: '/create',
    name: 'CreateTrip',
    component: lazyLoad(() => import('../views/CreateTrip.vue'))
  },
  {
    path: '/login',
    name: 'Login',
    component: lazyLoad(() => import('../views/Login.vue'))
  },
  {
    path: '/trips',
    name: 'MyTrips',
    meta: { requiresAuth: true },
    component: lazyLoad(() => import('../views/MyTrips.vue'))
  },
  {
    path: '/workbench',
    name: 'Workbench',
    component: () => import('../views/workbench/Workbench.vue')
  },
  // 404 兜底：未匹配的路径统一重定向到首页，避免空白页面
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    redirect: '/'
  }
]

// 创建路由实例
const router = createRouter({
  // history 模式，URL 里不会带 # 号
  history: createWebHistory(),
  routes,
  // 切换路由时回到页面顶部，并支持 hash 锚点跳转
  scrollBehavior(to, _from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    }
    if (to.hash) {
      return { el: to.hash, behavior: 'smooth' }
    }
    return { top: 0 }
  }
})

// 需要登录的页面：未登录时跳到登录页，并在登录后回跳
router.beforeEach((to) => {
  const userStore = useUserStore()
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/login' && userStore.isLoggedIn) {
    return { path: '/' }
  }
  return true
})

export default router
