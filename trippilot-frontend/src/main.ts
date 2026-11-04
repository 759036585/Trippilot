// src/main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
// 引入 Element Plus 组件库和样式
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
// 引入路由
import router from './router'
import App from './App.vue'

// 创建 Vue 应用
const app = createApp(App)

// 挂载状态管理 Pinia
app.use(createPinia())
// 挂载路由
app.use(router)
// 挂载 Element Plus
app.use(ElementPlus)

// 把应用挂载到 index.html 的 #app 节点上
app.mount('#app')