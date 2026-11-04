// src/stores/user.ts
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import request from '../api/request'

export interface AuthUser {
  id: number
  username: string
  nickname: string
}

const TOKEN_KEY = 'tp_token'
const USER_KEY = 'tp_user'

function readUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as AuthUser) : null
  } catch {
    return null
  }
}

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(localStorage.getItem(TOKEN_KEY) || '')
  const user = ref<AuthUser | null>(readUser())

  const isLoggedIn = computed(() => !!token.value)
  const displayName = computed(() => user.value?.nickname || user.value?.username || '旅行者')
  const initial = computed(() => (displayName.value || '旅').slice(0, 1).toUpperCase())

  function setSession(nextToken: string, nextUser: AuthUser) {
    token.value = nextToken
    user.value = nextUser
    localStorage.setItem(TOKEN_KEY, nextToken)
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser))
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  async function login(username: string, password: string) {
    const res: any = await request.post('/api/v1/auth/login', { username, password })
    setSession(res.token, res.user)
    return res
  }

  async function register(username: string, password: string, nickname?: string) {
    const res: any = await request.post('/api/v1/auth/register', { username, password, nickname })
    setSession(res.token, res.user)
    return res
  }

  /** 刷新页面后用本地 token 换回最新的用户信息，token 失效则自动登出 */
  async function refresh() {
    if (!token.value) return
    try {
      const res: any = await request.get('/api/v1/auth/me')
      user.value = res
      localStorage.setItem(USER_KEY, JSON.stringify(res))
    } catch {
      logout()
    }
  }

  return { token, user, isLoggedIn, displayName, initial, login, register, refresh, logout }
})
