<!-- src/views/Login.vue -->
<template>
  <div class="login-page">
    <!-- 左侧品牌介绍 -->
    <aside class="intro">
      <div class="intro__glow intro__glow--one"></div>
      <div class="intro__glow intro__glow--two"></div>

      <a class="intro__brand" href="/" @click.prevent="router.push('/')">
        <span class="intro__mark">✈</span>
        <span>旅程 AI</span>
      </a>

      <div class="intro__copy">
        <h1>{{ isRegister ? '开启你的第一段旅程' : '欢迎回来' }}</h1>
        <p>
          {{ isRegister
            ? '注册后，AI 为你生成的每一份行程都会自动保存，随时打开继续修改。'
            : '登录后即可查看历史行程，接着上次的规划继续出发。' }}
        </p>
      </div>

      <ul class="intro__list">
        <li><span>01</span>AI 自动排景点、交通与预算</li>
        <li><span>02</span>行程实时落地到地图，点击即定位</li>
        <li><span>03</span>历史行程永久保存，随时回看</li>
      </ul>
    </aside>

    <!-- 右侧表单 -->
    <main class="panel">
      <div class="card">
        <div class="card__head">
          <h2>{{ isRegister ? '注册账号' : '登录' }}</h2>
          <p>{{ isRegister ? '20 秒完成，立刻保存你的行程' : '使用用户名和密码登录' }}</p>
        </div>

        <form class="form" @submit.prevent="submit">
          <label class="field">
            <span class="field__label">用户名</span>
            <input
              v-model.trim="form.username"
              class="field__input"
              type="text"
              autocomplete="username"
              placeholder="3-32 个字符"
              maxlength="32"
            />
          </label>

          <label v-if="isRegister" class="field">
            <span class="field__label">昵称 <em>（可选）</em></span>
            <input
              v-model.trim="form.nickname"
              class="field__input"
              type="text"
              placeholder="显示在页面右上角"
              maxlength="32"
            />
          </label>

          <label class="field">
            <span class="field__label">密码</span>
            <div class="field__wrap">
              <input
                v-model="form.password"
                class="field__input"
                :type="showPassword ? 'text' : 'password'"
                :autocomplete="isRegister ? 'new-password' : 'current-password'"
                placeholder="至少 6 位"
                maxlength="64"
              />
              <button class="field__toggle" type="button" @click="showPassword = !showPassword">
                {{ showPassword ? '隐藏' : '显示' }}
              </button>
            </div>
          </label>

          <label v-if="isRegister" class="field">
            <span class="field__label">确认密码</span>
            <input
              v-model="form.confirm"
              class="field__input"
              :type="showPassword ? 'text' : 'password'"
              autocomplete="new-password"
              placeholder="再输入一次"
              maxlength="64"
            />
          </label>

          <p v-if="errorText" class="error">{{ errorText }}</p>

          <button class="submit" type="submit" :disabled="loading">
            <span v-if="loading" class="spinner"></span>
            {{ loading ? '处理中…' : isRegister ? '注册并开始使用' : '登录' }}
          </button>
        </form>

        <div class="switch">
          <span>{{ isRegister ? '已经有账号了？' : '还没有账号？' }}</span>
          <button type="button" @click="toggleMode">{{ isRegister ? '直接登录' : '免费注册' }}</button>
        </div>

        <div class="card__foot">
          <a href="/" @click.prevent="router.push('/')">← 返回首页</a>
          <span v-if="redirect" class="hint">登录后将回到之前的页面</span>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'
import { errorMessage } from '../api/request'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const mode = ref<'login' | 'register'>('login')
const isRegister = computed(() => mode.value === 'register')
const loading = ref(false)
const errorText = ref('')
const showPassword = ref(false)
const redirect = computed(() => (typeof route.query.redirect === 'string' ? route.query.redirect : ''))

const form = reactive({
  username: '',
  password: '',
  confirm: '',
  nickname: ''
})

const toggleMode = () => {
  mode.value = isRegister.value ? 'login' : 'register'
  errorText.value = ''
  form.password = ''
  form.confirm = ''
}

const validate = (): string => {
  if (form.username.length < 3) return '用户名至少 3 个字符'
  if (form.username.length > 32) return '用户名最多 32 个字符'
  if (form.password.length < 6) return '密码至少 6 位'
  if (isRegister.value && form.password !== form.confirm) return '两次输入的密码不一致'
  return ''
}

const submit = async () => {
  if (loading.value) return
  errorText.value = validate()
  if (errorText.value) return

  loading.value = true
  try {
    if (isRegister.value) {
      await userStore.register(form.username, form.password, form.nickname || undefined)
      ElMessage.success(`注册成功，欢迎你，${userStore.displayName}`)
    } else {
      await userStore.login(form.username, form.password)
      ElMessage.success(`欢迎回来，${userStore.displayName}`)
    }
    router.replace(redirect.value || '/trips')
  } catch (err) {
    errorText.value = errorMessage(err, '登录失败，请稍后再试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  background: #f8fafc;
}

/* ---------- 左侧 ---------- */
.intro {
  position: relative;
  overflow: hidden;
  padding: 40px 56px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  color: #fff;
  background: linear-gradient(150deg, #0f766e 0%, #0d9488 45%, #134e4a 100%);
}

.intro__glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.5;
  pointer-events: none;
}

.intro__glow--one {
  width: 380px;
  height: 380px;
  top: -120px;
  right: -80px;
  background: #5eead4;
}

.intro__glow--two {
  width: 320px;
  height: 320px;
  bottom: -140px;
  left: -60px;
  background: #f59e0b;
  opacity: 0.28;
}

.intro__brand {
  position: absolute;
  top: 40px;
  left: 56px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 17px;
  font-weight: 700;
  color: #fff;
  text-decoration: none;
  letter-spacing: 0.5px;
}

.intro__mark {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.28);
}

.intro__copy {
  position: relative;
  margin: 0 0 32px;
  max-width: 460px;
}

.intro__copy h1 {
  font-size: clamp(30px, 3.4vw, 44px);
  line-height: 1.2;
  margin: 0 0 16px;
  letter-spacing: 1px;
}

.intro__copy p {
  margin: 0;
  font-size: 15px;
  line-height: 1.9;
  color: rgba(255, 255, 255, 0.82);
}

.intro__list {
  position: relative;
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 12px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.86);
}

.intro__list li {
  display: flex;
  align-items: center;
  gap: 12px;
}

.intro__list span {
  font-size: 12px;
  font-weight: 700;
  color: #0f766e;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 999px;
  padding: 3px 8px;
}

/* ---------- 右侧 ---------- */
.panel {
  display: grid;
  place-items: center;
  padding: 40px 24px;
}

.card {
  width: 100%;
  max-width: 400px;
}

.card__head h2 {
  margin: 0 0 6px;
  font-size: 26px;
  color: #0f172a;
  letter-spacing: 0.5px;
}

.card__head p {
  margin: 0 0 28px;
  font-size: 14px;
  color: #64748b;
}

.form {
  display: grid;
  gap: 16px;
}

.field {
  display: grid;
  gap: 7px;
}

.field__label {
  font-size: 13px;
  font-weight: 500;
  color: #334155;
}

.field__label em {
  font-style: normal;
  color: #94a3b8;
  font-weight: 400;
}

.field__wrap {
  position: relative;
}

.field__input {
  width: 100%;
  height: 44px;
  padding: 0 14px;
  border-radius: 11px;
  border: 1px solid #e2e8f0;
  background: #fff;
  font-size: 14px;
  font-family: inherit;
  color: #0f172a;
  outline: none;
  transition: border-color 0.18s, box-shadow 0.18s;
}

.field__input::placeholder {
  color: #cbd5e1;
}

.field__input:focus {
  border-color: #0d9488;
  box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.12);
}

.field__wrap .field__input {
  padding-right: 58px;
}

.field__toggle {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  border: none;
  background: transparent;
  font-size: 12px;
  font-family: inherit;
  color: #0d9488;
  cursor: pointer;
  padding: 6px;
}

.error {
  margin: 0;
  padding: 9px 12px;
  border-radius: 9px;
  font-size: 13px;
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.submit {
  margin-top: 4px;
  height: 46px;
  border: none;
  border-radius: 11px;
  font-size: 15px;
  font-weight: 600;
  font-family: inherit;
  color: #fff;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: linear-gradient(135deg, #14b8a6, #0d9488);
  box-shadow: 0 10px 24px rgba(13, 148, 136, 0.28);
  transition: transform 0.18s, box-shadow 0.18s, opacity 0.18s;
}

.submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 14px 28px rgba(13, 148, 136, 0.34);
}

.submit:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.spinner {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.45);
  border-top-color: #fff;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.switch {
  margin-top: 18px;
  font-size: 13px;
  color: #64748b;
  display: flex;
  gap: 6px;
  justify-content: center;
}

.switch button {
  border: none;
  background: none;
  padding: 0;
  color: #0d9488;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.card__foot {
  margin-top: 26px;
  padding-top: 18px;
  border-top: 1px solid #eef2f7;
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.card__foot a {
  color: #64748b;
  text-decoration: none;
}

.card__foot a:hover {
  color: #0d9488;
}

.hint {
  color: #94a3b8;
}

@media (max-width: 900px) {
  .login-page {
    grid-template-columns: 1fr;
  }
  .intro {
    padding: 26px 22px 34px;
    justify-content: flex-start;
  }
  .intro__brand {
    position: static;
  }
  .intro__copy {
    margin: 28px 0 22px;
  }
  .intro__list {
    display: none;
  }
  .panel {
    padding: 28px 20px 48px;
  }
}
</style>
