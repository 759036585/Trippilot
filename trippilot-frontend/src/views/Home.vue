<!-- src/views/Home.vue 首页 -->
<template>
  <div class="home">
    <AppHeader />

    <!-- ---------- Hero ---------- -->
    <section class="hero">
      <div class="hero__glow hero__glow--teal"></div>
      <div class="hero__glow hero__glow--blue"></div>
      <div class="hero__grid"></div>

      <div class="hero__inner">
        <span class="badge">
          <span class="badge__dot"></span>
          AI 行程规划 · 接入真实地图数据
        </span>

        <h1>
          把旅行交给 AI
          <br />
          <span class="grad">说走就走，不再慌张</span>
        </h1>

        <p class="hero__desc">
          和 AI 聊几句说清想去哪儿、什么时候走、预算多少，它会自动生成城际交通、酒店住宿、
          每天的景点路线，以及交通 / 住宿 / 餐饮 / 门票的分类预算。
        </p>

        <div class="search">
          <el-icon class="search__icon"><Search /></el-icon>
          <input
            v-model.trim="destination"
            class="search__input"
            type="text"
            placeholder="想去哪里？如：成都、大理、厦门"
            maxlength="30"
            @keyup.enter="goCreate()"
          />
          <button class="search__btn" type="button" @click="goCreate()">
            开始规划
            <el-icon><ArrowRight /></el-icon>
          </button>
        </div>

        <div class="hot">
          <span class="hot__label">热门目的地</span>
          <button
            v-for="city in hotCities"
            :key="city"
            class="hot__chip"
            type="button"
            @click="goCreate(city)"
          >
            {{ city }}
          </button>
        </div>

        <ul class="pillars">
          <li>
            <span class="pillars__icon pillars__icon--teal">
              <el-icon><MapLocation /></el-icon>
            </span>
            <div>
              <strong>真实地图数据</strong>
              <small>高德 POI 与驾车路线</small>
            </div>
          </li>
          <li>
            <span class="pillars__icon pillars__icon--amber">
              <el-icon><MagicStick /></el-icon>
            </span>
            <div>
              <strong>AI 自动排程</strong>
              <small>每天几点去哪都安排好</small>
            </div>
          </li>
          <li>
            <span class="pillars__icon pillars__icon--violet">
              <el-icon><Wallet /></el-icon>
            </span>
            <div>
              <strong>预算一目了然</strong>
              <small>花费与预算实时对比</small>
            </div>
          </li>
        </ul>
      </div>
    </section>

    <!-- ---------- 能力介绍 ---------- -->
    <section class="section">
      <div class="section__head">
        <h2>一次输入，整套行程</h2>
        <p>从想法到可执行的行程，AI 帮你把中间所有麻烦事都做完</p>
      </div>

      <div class="features">
        <article v-for="feature in features" :key="feature.title" class="feature">
          <span class="feature__icon" :style="{ background: feature.bg, color: feature.color }">
            <el-icon><component :is="feature.icon" /></el-icon>
          </span>
          <h3>{{ feature.title }}</h3>
          <p>{{ feature.desc }}</p>
        </article>
      </div>
    </section>

    <!-- ---------- 发现目的地 ---------- -->
    <section id="discover" class="section section--discover">
      <div class="section__head section__head--row">
        <div>
          <h2>发现目的地</h2>
          <p>挑一个心动的地方，剩下的交给 AI</p>
        </div>
        <span class="section__hint">点击卡片即可带着目的地开始规划 →</span>
      </div>

      <div class="dest-grid">
        <button
          v-for="dest in destinations"
          :key="dest.name"
          class="dest"
          type="button"
          :style="{ background: dest.gradient }"
          @click="goCreate(dest.name)"
        >
          <span class="dest__emoji">{{ dest.emoji }}</span>
          <span class="dest__no">{{ dest.days }}</span>
          <div class="dest__body">
            <h3>{{ dest.name }}</h3>
            <p>{{ dest.keywords }}</p>
            <div class="dest__tags">
              <span v-for="tag in dest.tags" :key="tag">{{ tag }}</span>
            </div>
          </div>
          <span class="dest__arrow">
            <el-icon><ArrowRight /></el-icon>
          </span>
        </button>
      </div>
    </section>

    <!-- ---------- 登录引导 ---------- -->
    <section class="section">
      <div class="cta">
        <div class="cta__glow"></div>
        <div class="cta__actions">
          <template v-if="userStore.isLoggedIn">
            <button class="cta__btn cta__btn--solid" type="button" @click="router.push('/trips')">
              查看我的行程
            </button>
            <button class="cta__btn cta__btn--ghost" type="button" @click="goCreate()">规划新旅程</button>
          </template>
          <template v-else>
            <button class="cta__btn cta__btn--solid" type="button" @click="router.push('/login')">
              免费注册 / 登录
            </button>
            <button class="cta__btn cta__btn--ghost" type="button" @click="goCreate()">先体验一下</button>
          </template>
        </div>
      </div>
    </section>

    <footer class="footer">
      <span>✈ 旅程 AI</span>
      <span class="footer__dot">·</span>
      <span>AI 行程规划 Demo</span>
      <span class="footer__dot">·</span>
      <span>地图数据来自高德</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowRight,
  MagicStick,
  MapLocation,
  Search,
  Wallet,
  Place,
  Coin
} from '@element-plus/icons-vue'
import AppHeader from '../components/AppHeader.vue'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const destination = ref('')

const hotCities = ['成都', '大理', '厦门', '西安', '重庆', '杭州']

const goCreate = (city?: string) => {
  const target = (city ?? destination.value).trim()
  router.push({
    path: '/create',
    query: target ? { destination: target } : undefined
  })
}

const features = [
  {
    icon: MagicStick,
    title: 'AI 生成每日行程',
    desc: '告诉 AI 你的偏好，自动安排每一天的景点、用餐与游玩时长，时间衔接合理。',
    bg: 'rgba(13, 148, 136, 0.1)',
    color: '#0d9488'
  },
  {
    icon: Place,
    title: '真实路线与耗时',
    desc: '景点之间自动计算驾车距离和耗时，地图上画出真实道路，不做纸上谈兵。',
    bg: 'rgba(249, 115, 22, 0.12)',
    color: '#ea580c'
  },
  {
    icon: Coin,
    title: '预算实时对比',
    desc: '每个地点的花费累加，和你的总预算实时对比，超支前就能发现。',
    bg: 'rgba(139, 92, 246, 0.12)',
    color: '#7c3aed'
  }
]

const destinations = [
  { name: '成都', emoji: '🐼', days: '3 天 2 晚', keywords: '火锅 · 熊猫 · 慢生活', tags: ['美食', '亲子'], gradient: 'linear-gradient(140deg, #f97316, #b91c1c)' },
  { name: '大理', emoji: '🌾', days: '4 天 3 晚', keywords: '洱海 · 苍山 · 古城', tags: ['慢旅行', '拍照'], gradient: 'linear-gradient(140deg, #0ea5e9, #1e40af)' },
  { name: '厦门', emoji: '🌴', days: '3 天 2 晚', keywords: '海岛 · 鼓浪屿 · 文艺', tags: ['海岛', '休闲'], gradient: 'linear-gradient(140deg, #06b6d4, #0f766e)' },
  { name: '西安', emoji: '🏯', days: '3 天 2 晚', keywords: '城墙 · 兵马俑 · 面食', tags: ['历史', '人文'], gradient: 'linear-gradient(140deg, #b45309, #7c2d12)' },
  { name: '重庆', emoji: '🌉', days: '2 天 1 晚', keywords: '山城 · 夜景 · 江景', tags: ['夜景', '美食'], gradient: 'linear-gradient(140deg, #8b5cf6, #4c1d95)' },
  { name: '杭州', emoji: '⛩️', days: '2 天 1 晚', keywords: '西湖 · 茶园 · 宋韵', tags: ['周末', '城市'], gradient: 'linear-gradient(140deg, #10b981, #065f46)' }
]
</script>

<style scoped>
.home {
  min-height: 100vh;
  background: #f8fafc;
  color: #0f172a;
}

/* ---------- Hero ---------- */
.hero {
  position: relative;
  overflow: hidden;
  padding: 76px 24px 50px;
  background:
    radial-gradient(900px 400px at 50% -180px, #ccfbf1 0%, rgba(204, 251, 241, 0) 72%),
    linear-gradient(180deg, #f8fbff 0%, #f5f9fc 100%);
}

.hero__glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
}

.hero__glow--teal {
  width: 420px;
  height: 420px;
  top: -160px;
  left: -120px;
  background: rgba(45, 212, 191, 0.32);
}

.hero__glow--blue {
  width: 380px;
  height: 380px;
  top: -120px;
  right: -140px;
  background: rgba(125, 211, 252, 0.3);
}

.hero__grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(15, 23, 42, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 23, 42, 0.045) 1px, transparent 1px);
  background-size: 46px 46px;
  mask-image: radial-gradient(600px 320px at 50% 0%, #000 0%, transparent 78%);
  -webkit-mask-image: radial-gradient(600px 320px at 50% 0%, #000 0%, transparent 78%);
  pointer-events: none;
}

.hero__inner {
  position: relative;
  max-width: 860px;
  margin: 0 auto;
  text-align: center;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 12.5px;
  letter-spacing: 0.4px;
  color: #0f766e;
  background: rgba(240, 253, 250, 0.9);
  border: 1px solid rgba(13, 148, 136, 0.22);
  box-shadow: 0 4px 14px rgba(13, 148, 136, 0.08);
}

.badge__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #14b8a6;
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.18);
}

.hero h1 {
  margin: 22px 0 16px;
  font-size: clamp(32px, 4.6vw, 54px);
  line-height: 1.22;
  letter-spacing: 1px;
  font-weight: 800;
}

.grad {
  background: linear-gradient(100deg, #0d9488 0%, #0284c7 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.hero__desc {
  max-width: 640px;
  margin: 0 auto 30px;
  font-size: 15.5px;
  line-height: 1.9;
  color: #64748b;
}

.search {
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: 680px;
  margin: 0 auto;
  padding: 6px 6px 6px 18px;
  background: #fff;
  border: 1px solid #e5edf4;
  border-radius: 16px;
  box-shadow: 0 20px 44px rgba(15, 23, 42, 0.1), 0 2px 6px rgba(15, 23, 42, 0.04);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.search:focus-within {
  border-color: #5eead4;
  box-shadow: 0 20px 44px rgba(13, 148, 136, 0.16), 0 0 0 4px rgba(20, 184, 166, 0.1);
}

.search__icon {
  color: #94a3b8;
  font-size: 18px;
  flex-shrink: 0;
}

.search__input {
  flex: 1;
  min-width: 0;
  height: 48px;
  border: none;
  outline: none;
  background: transparent;
  font-size: 15.5px;
  font-family: inherit;
  color: #0f172a;
}

.search__input::placeholder {
  color: #a9b6c6;
}

.search__btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 48px;
  padding: 0 24px;
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-family: inherit;
  font-weight: 500;
  color: #fff;
  white-space: nowrap;
  cursor: pointer;
  background: linear-gradient(135deg, #14b8a6, #0d9488);
  box-shadow: 0 10px 22px rgba(13, 148, 136, 0.3);
  transition: transform 0.18s, box-shadow 0.18s;
}

.search__btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 26px rgba(13, 148, 136, 0.36);
}

.hot {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 18px;
}

.hot__label {
  font-size: 12.5px;
  color: #94a3b8;
  margin-right: 2px;
}

.hot__chip {
  padding: 5px 13px;
  border-radius: 999px;
  border: 1px solid #e6edf4;
  background: rgba(255, 255, 255, 0.8);
  font-size: 12.5px;
  font-family: inherit;
  color: #475569;
  cursor: pointer;
  transition: all 0.16s;
}

.hot__chip:hover {
  border-color: #99f6e4;
  color: #0d9488;
  background: #f0fdfa;
}

.pillars {
  list-style: none;
  margin: 52px auto 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  max-width: 780px;
}

.pillars li {
  display: flex;
  align-items: center;
  gap: 12px;
  text-align: left;
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(226, 232, 240, 0.9);
  backdrop-filter: blur(6px);
}

.pillars strong {
  display: block;
  font-size: 13.5px;
  color: #1e293b;
  margin-bottom: 2px;
}

.pillars small {
  font-size: 12px;
  color: #94a3b8;
}

.pillars__icon {
  width: 36px;
  height: 36px;
  border-radius: 11px;
  display: grid;
  place-items: center;
  font-size: 17px;
  flex-shrink: 0;
}

.pillars__icon--teal {
  background: rgba(13, 148, 136, 0.12);
  color: #0d9488;
}

.pillars__icon--amber {
  background: rgba(245, 158, 11, 0.14);
  color: #d97706;
}

.pillars__icon--violet {
  background: rgba(139, 92, 246, 0.14);
  color: #7c3aed;
}

/* ---------- 通用 Section ---------- */
.section {
  max-width: 1140px;
  margin: 0 auto;
  padding: 54px 24px 0;
}

.section__head {
  text-align: center;
  margin-bottom: 32px;
}

.section__head h2 {
  margin: 0 0 10px;
  font-size: clamp(22px, 2.6vw, 30px);
  letter-spacing: 0.6px;
}

.section__head p {
  margin: 0;
  font-size: 14.5px;
  color: #64748b;
}

.section__head--row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  text-align: left;
}

.section__hint {
  font-size: 13px;
  color: #94a3b8;
}

/* ---------- 能力卡片 ---------- */
.features {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.feature {
  padding: 26px 24px;
  border-radius: 18px;
  background: #fff;
  border: 1px solid #eef2f7;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
}

.feature:hover {
  transform: translateY(-4px);
  border-color: #e0f2fe;
  box-shadow: 0 18px 34px rgba(15, 23, 42, 0.08);
}

.feature__icon {
  width: 44px;
  height: 44px;
  border-radius: 13px;
  display: grid;
  place-items: center;
  font-size: 21px;
  margin-bottom: 16px;
}

.feature h3 {
  margin: 0 0 8px;
  font-size: 16.5px;
  color: #0f172a;
}

.feature p {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.85;
  color: #64748b;
}

/* ---------- 发现目的地 ---------- */
.section--discover {
  scroll-margin-top: 80px;
}

.dest-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 18px;
}

.dest {
  position: relative;
  height: 224px;
  padding: 22px;
  border: none;
  border-radius: 18px;
  overflow: hidden;
  text-align: left;
  color: #fff;
  font-family: inherit;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.14);
  transition: transform 0.22s, box-shadow 0.22s;
}

.dest::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image: radial-gradient(rgba(255, 255, 255, 0.4) 1px, transparent 1px);
  background-size: 18px 18px;
  opacity: 0.22;
  pointer-events: none;
}

.dest:hover {
  transform: translateY(-6px);
  box-shadow: 0 22px 40px rgba(15, 23, 42, 0.22);
}

.dest__emoji {
  position: absolute;
  top: -16px;
  right: -6px;
  font-size: 112px;
  line-height: 1;
  opacity: 0.22;
  filter: blur(0.3px);
}

.dest__no {
  position: absolute;
  top: 18px;
  left: 22px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11.5px;
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(4px);
}

.dest__body {
  position: relative;
  z-index: 1;
}

.dest__body h3 {
  margin: 0 0 6px;
  font-size: 24px;
  letter-spacing: 1px;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.18);
}

.dest__body p {
  margin: 0 0 12px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
}

.dest__tags {
  display: flex;
  gap: 8px;
}

.dest__tags span {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11.5px;
  background: rgba(255, 255, 255, 0.16);
  border: 1px solid rgba(255, 255, 255, 0.24);
}

.dest__arrow {
  position: absolute;
  right: 20px;
  bottom: 22px;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: rgba(255, 255, 255, 0.92);
  color: #0f172a;
  z-index: 1;
  transition: transform 0.2s;
}

.dest:hover .dest__arrow {
  transform: translateX(4px);
}

/* ---------- CTA ---------- */
.cta {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  padding: 32px 44px;
  border-radius: 22px;
  color: #fff;
  background: linear-gradient(120deg, #0f766e 0%, #0d9488 55%, #134e4a 100%);
  box-shadow: 0 22px 46px rgba(13, 148, 136, 0.26);
}

.cta__glow {
  position: absolute;
  width: 340px;
  height: 340px;
  right: -80px;
  top: -140px;
  border-radius: 50%;
  background: rgba(94, 234, 212, 0.35);
  filter: blur(70px);
}

.cta__actions {
  position: relative;
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

.cta__btn {
  height: 44px;
  padding: 0 20px;
  border-radius: 11px;
  font-size: 14px;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.18s;
}

.cta__btn--solid {
  border: none;
  background: #fff;
  color: #0f766e;
  font-weight: 600;
}

.cta__btn--solid:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.14);
}

.cta__btn--ghost {
  border: 1px solid rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.cta__btn--ghost:hover {
  background: rgba(255, 255, 255, 0.18);
}

/* ---------- Footer ---------- */
.footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 46px 24px 40px;
  font-size: 12.5px;
  color: #94a3b8;
}

.footer__dot {
  color: #cbd5e1;
}

@media (max-width: 900px) {
  .pillars {
    grid-template-columns: 1fr;
    max-width: 420px;
  }
  .features {
    grid-template-columns: 1fr;
  }
  .section__head--row {
    flex-direction: column;
    align-items: flex-start;
  }
  .section__hint {
    display: none;
  }
  .cta {
    flex-direction: column;
    align-items: flex-start;
    padding: 30px 26px;
  }
}

@media (max-width: 640px) {
  .hero {
    padding: 48px 16px 48px;
  }
  .search {
    flex-direction: column;
    padding: 10px;
    gap: 8px;
  }
  .search__icon {
    display: none;
  }
  .search__input {
    width: 100%;
    height: 44px;
    padding: 0 8px;
    border-bottom: 1px solid #eef2f7;
  }
  .search__btn {
    width: 100%;
    justify-content: center;
  }
  .section {
    padding: 46px 16px 0;
  }
  .dest {
    height: 190px;
  }
  .cta__actions {
    width: 100%;
    flex-direction: column;
  }
  .cta__btn {
    width: 100%;
  }
}
</style>
