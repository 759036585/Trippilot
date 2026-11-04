// src/views/workbench/useNearby.ts
// 周边推荐：分类 / 半径切换、列表请求、地图预览联动
import { computed, ref, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../../api/request'
import { CATEGORY_ICONS, NEARBY_RADII } from './constants'
import { hasCoords } from './format'
import type { NearbyPoi, TripItem } from './types'

interface UseNearbyOptions {
  /** 当前选中的行程地点，周边推荐以它为中心 */
  activeItem: Ref<TripItem | null>
  /** 在地图上展示 POI 预览；返回 false 表示地图没准备好 */
  onPreview: (poi: NearbyPoi) => boolean | void
  /** 清除地图上的 POI 预览 / 标记 */
  onClearPreview: () => void
}

export function useNearby(options: UseNearbyOptions) {
  const nearby = ref<NearbyPoi[]>([])
  const nearbyLoading = ref(false)
  const nearbyCategory = ref('scenic')
  const nearbyRadius = ref(NEARBY_RADII[1])
  const previewPoiId = ref('')

  const categoryFallback = computed(() => CATEGORY_ICONS[nearbyCategory.value] ?? '📍')

  let requestSeq = 0

  async function loadNearby() {
    const item = options.activeItem.value
    const seq = ++requestSeq
    if (!item || !hasCoords(item)) {
      nearby.value = []
      return
    }

    nearbyLoading.value = true
    try {
      const res: any = await request.get('/api/v1/pois/nearby', {
        params: {
          lng: item.lng,
          lat: item.lat,
          category: nearbyCategory.value,
          radius: nearbyRadius.value,
          limit: 10
        }
      })
      if (seq !== requestSeq) return
      nearby.value = res?.pois ?? []
    } catch {
      if (seq !== requestSeq) return
      nearby.value = []
      ElMessage.error('周边推荐加载失败，请稍后再试')
    } finally {
      if (seq === requestSeq) nearbyLoading.value = false
    }
  }

  function switchCategory(key: string) {
    if (nearbyCategory.value === key) return
    nearbyCategory.value = key
    previewPoiId.value = ''
    options.onClearPreview()
    loadNearby()
  }

  function switchRadius(value: number) {
    if (nearbyRadius.value === value) return
    nearbyRadius.value = value
    loadNearby()
  }

  function previewPoi(poi: NearbyPoi) {
    const shown = options.onPreview(poi)
    if (shown !== false) previewPoiId.value = poi.id
  }

  /** 取消选中（换地点 / 切分类时用） */
  function resetPreview() {
    previewPoiId.value = ''
    options.onClearPreview()
  }

  return {
    nearby,
    nearbyLoading,
    nearbyCategory,
    nearbyRadius,
    previewPoiId,
    categoryFallback,
    loadNearby,
    switchCategory,
    switchRadius,
    previewPoi,
    resetPreview
  }
}
