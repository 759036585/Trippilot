// src/api/request.ts
import axios from 'axios'

// 后端地址从 .env.local 读取（VITE_API_BASE_URL）
// 没配置 → 本地开发默认 8000 端口；显式配置为空串 → 走同源，由 nginx 反代 /api（生产部署用）
const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/+$/, '')

// 创建一个 axios 实例，统一配置
const request = axios.create({
  baseURL: BASE_URL,
  timeout: 10000 // 请求超时时间：10秒
})

// 请求拦截器：带上登录 token
request.interceptors.request.use(config => {
  const token = localStorage.getItem('tp_token')
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：成功时直接返回 data；401 时通知全局清理登录态
request.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    if (error.response?.status === 401) {
      // App.vue 里监听这个事件，清空 Pinia 中的用户状态
      window.dispatchEvent(new CustomEvent('tp:unauthorized'))
    }
    return Promise.reject(error)
  }
)

/** 从后端错误里取出可读的中文提示 */
export function errorMessage(err: any, fallback = '请求失败，请稍后再试'): string {
  return (
    err?.response?.data?.detail ||
    err?.response?.data?.message ||
    (err?.code === 'ECONNABORTED' ? '请求超时，请检查后端服务是否已启动' : '') ||
    err?.message ||
    fallback
  )
}

export default request
