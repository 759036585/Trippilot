<!-- src/views/workbench/components/NearbyPanel.vue -->
<!-- 右栏中部：以当前地点为中心的周边推荐 -->
<template>
  <section class="nearby-card">
    <div class="nearby-head">
      <div>
        <h4>周边推荐</h4>
        <p class="nearby-sub">
          {{ activeItem ? `围绕「${activeItem.place_name}」` : '点击左侧地点查看附近' }}
        </p>
      </div>
      <el-icon class="nearby-icon"><LocationFilled /></el-icon>
    </div>

    <div class="nearby-tabs">
      <button
        v-for="cat in NEARBY_CATEGORIES"
        :key="cat.key"
        class="nearby-tab"
        :class="{ on: category === cat.key }"
        @click="emit('switch-category', cat.key)"
      >{{ cat.label }}</button>
    </div>

    <div class="radius-row">
      <button
        v-for="r in NEARBY_RADII"
        :key="r"
        class="radius-chip"
        :class="{ on: radius === r }"
        @click="emit('switch-radius', r)"
      >{{ r / 1000 }}km 内</button>
    </div>

    <div class="nearby-list" v-loading="loading">
      <template v-if="nearby.length">
        <article
          v-for="poi in nearby"
          :key="poi.id"
          class="poi-card"
          :class="{ active: previewId === poi.id }"
          @click="emit('preview', poi)"
        >
          <div
            class="poi-thumb"
            :style="poi.photo ? { backgroundImage: `url(${poi.photo})` } : {}"
          >
            <span v-if="!poi.photo" class="poi-thumb__icon">{{ categoryFallback }}</span>
          </div>
          <div class="poi-body">
            <div class="poi-name">{{ poi.name }}</div>
            <div class="poi-meta">
              <span class="poi-rating" v-if="poi.rating">★ {{ poi.rating }}</span>
              <span class="poi-dist">{{ fmtDist(poi.distance) }}</span>
            </div>
            <div class="poi-addr">{{ poi.address || poi.type }}</div>
          </div>
          <button class="poi-add" title="加入当天行程" @click.stop="emit('add', poi)">+</button>
        </article>
      </template>
      <div v-else-if="!loading" class="nearby-empty">
        <p v-if="!activeItem">先在上方选择一个地点吧</p>
        <p v-else>当前范围内暂无可推荐的地点</p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { LocationFilled } from '@element-plus/icons-vue'
import { CATEGORY_ICONS, NEARBY_CATEGORIES, NEARBY_RADII } from '../constants'
import { fmtDist } from '../format'
import type { NearbyPoi, TripItem } from '../types'

const props = defineProps<{
  activeItem: TripItem | null
  nearby: NearbyPoi[]
  loading: boolean
  category: string
  radius: number
  previewId: string
}>()

const emit = defineEmits<{
  'switch-category': [key: string]
  'switch-radius': [radius: number]
  preview: [poi: NearbyPoi]
  add: [poi: NearbyPoi]
}>()

const categoryFallback = computed(() => CATEGORY_ICONS[props.category] ?? '📍')
</script>

<style scoped>
.nearby-card {
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1 1 auto;
  min-height: 0;
}
.nearby-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.nearby-head h4 {
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
.nearby-icon {
  color: #cbd5e1;
  font-size: 16px;
}
.nearby-tabs {
  display: flex;
  gap: 4px;
  background: #f4f7f8;
  border-radius: 10px;
  padding: 3px;
}
.nearby-tab {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 12px;
  color: var(--muted);
  padding: 7px 0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.16s;
}
.nearby-tab.on {
  background: #fff;
  color: var(--teal-dark);
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
}
.radius-row {
  display: flex;
  gap: 6px;
}
.radius-chip {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--muted);
  font-size: 11px;
  padding: 3px 9px;
  border-radius: 999px;
  cursor: pointer;
}
.radius-chip.on {
  border-color: #b8e6df;
  background: var(--teal-soft);
  color: var(--teal-dark);
  font-weight: 600;
}
.nearby-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1 1 auto;
  min-height: 60px;
  overflow-y: auto;
  padding-right: 2px;
  scrollbar-width: thin;
}
.nearby-list::-webkit-scrollbar {
  width: 5px;
}
.nearby-list::-webkit-scrollbar-thumb {
  background: #dbe4e9;
  border-radius: 3px;
}
.poi-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: 12px;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.16s;
  position: relative;
}
.poi-card:hover {
  background: #f8fbfc;
  border-color: var(--line);
}
.poi-card.active {
  background: var(--teal-soft);
  border-color: #b8e6df;
}
.poi-thumb {
  width: 48px;
  height: 48px;
  flex: 0 0 48px;
  border-radius: 10px;
  background: linear-gradient(135deg, #d7f2ec, #e8eef2);
  background-size: cover;
  background-position: center;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
  color: var(--teal-dark);
  overflow: hidden;
}
.poi-thumb__icon {
  font-size: 20px;
  line-height: 1;
}
.poi-body {
  min-width: 0;
  flex: 1;
}
.poi-name {
  font-size: 12.5px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.poi-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--muted);
  margin-top: 2px;
}
.poi-rating {
  color: #f59e0b;
  font-weight: 600;
}
.poi-addr {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.poi-add {
  width: 24px;
  height: 24px;
  flex: 0 0 24px;
  border-radius: 8px;
  border: 1px solid #d5e8e4;
  background: #fff;
  color: var(--teal-dark);
  font-size: 15px;
  line-height: 1;
  cursor: pointer;
  opacity: 0;
  transition: all 0.16s;
}
.poi-card:hover .poi-add {
  opacity: 1;
}
.poi-add:hover {
  background: var(--teal);
  border-color: var(--teal);
  color: #fff;
}
.nearby-empty {
  text-align: center;
  color: #a8b4bf;
  font-size: 12px;
  padding: 26px 0;
}
</style>
