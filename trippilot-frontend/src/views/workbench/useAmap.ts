// src/views/workbench/useAmap.ts
// 高德地图的加载、实例、标记、路线图层、信息窗体
// 只负责「怎么画」，点了哪个地点交给外部 onSelectItem 处理
import { nextTick, ref, type Ref } from 'vue'
import {
  dayColor,
  esc,
  fmtDate,
  fmtDist,
  fmtMoney,
  hasCoords
} from './format'
import type { NearbyPoi, RouteInfo, TripDay, TripItem } from './types'

const AMAP_KEY = import.meta.env.VITE_AMAP_JS_KEY as string | undefined
const AMAP_SECURITY_CODE = import.meta.env.VITE_AMAP_SECURITY_CODE as string | undefined

declare global {
  interface Window {
    _AMapSecurityConfig?: { securityJsCode: string }
    AMap?: any
    __amapLoadedKey?: string
    ___onAPILoaded?: (error?: unknown) => void
  }
}

// 整个页面只加载一次 SDK
let amapPromise: Promise<any> | null = null

function loadAMap(): Promise<any> {
  if (window.AMap) {
    if (window.__amapLoadedKey !== AMAP_KEY) {
      return Promise.reject(
        new Error('页面上的高德 SDK 是用旧 Key 加载的（热更新遗留），请按 Ctrl+Shift+R 强制刷新页面')
      )
    }
    return Promise.resolve(window.AMap)
  }
  if (amapPromise) return amapPromise

  amapPromise = new Promise((resolve, reject) => {
    window.___onAPILoaded = (error?: unknown) => {
      delete window.___onAPILoaded
      if (error) {
        amapPromise = null
        reject(new Error(String(error)))
        return
      }
      window.__amapLoadedKey = AMAP_KEY
      resolve(window.AMap)
    }

    const script = document.createElement('script')
    script.src =
      `https://webapi.amap.com/maps?callback=___onAPILoaded&v=2.0` +
      `&key=${encodeURIComponent(AMAP_KEY!)}&plugin=AMap.Scale,AMap.ToolBar`
    script.onerror = () => {
      amapPromise = null
      script.remove()
      reject(new Error('高德 JS API 脚本加载失败，请检查网络或 Key 的域名白名单'))
    }
    document.head.appendChild(script)
  })

  return amapPromise
}

interface UseAmapOptions {
  days: Ref<TripDay[]>
  activeItem: Ref<TripItem | null>
  segmentOf: (dayIndex: number, index: number) => RouteInfo | undefined
  onSelectItem: (item: TripItem, day: TripDay) => void
}

export function useAmap(options: UseAmapOptions) {
  let AMapLib: any = null

  const mapInstance = ref<any>(null)
  const mapError = ref('')
  const mapDay = ref(0)

  let dayMarkers: any[] = []
  let dayPolylines: any[] = []
  let nearbyMarkers: any[] = []
  const markerEls = new Map<number, HTMLElement>()
  let infoWindow: any = null
  let previewInfo: any = null

  async function ensureMap() {
    mapError.value = ''
    if (!AMAP_KEY) {
      mapError.value = '未配置高德地图 Key：请在 .env.local 填写 VITE_AMAP_JS_KEY 后重启 npm run dev。'
      return false
    }
    if (mapInstance.value) {
      mapInstance.value.resize()
      return true
    }

    if (AMAP_SECURITY_CODE) {
      window._AMapSecurityConfig = { securityJsCode: AMAP_SECURITY_CODE }
    }

    try {
      AMapLib = await loadAMap()
      const first = firstCoord()
      const map = new AMapLib.Map('amap-container', {
        zoom: 12,
        center: first || [116.397428, 39.90923],
        viewMode: '2D',
        mapStyle: 'amap://styles/whitesmoke',
        resizeEnable: true,
        showIndoorMap: false
      })
      mapInstance.value = map

      infoWindow = new AMapLib.InfoWindow({
        isCustom: true,
        offset: new AMapLib.Pixel(0, -6),
        autoMove: true
      })
      previewInfo = new AMapLib.InfoWindow({
        isCustom: true,
        offset: new AMapLib.Pixel(0, -6),
        autoMove: true
      })

      map.on('click', () => {
        infoWindow?.close()
      })
      map.on('zoomend', () => syncLabelVisibility())
      if (AMapLib.Scale) {
        map.addControl(new AMapLib.Scale({ position: 'LB' }))
      }
      return true
    } catch (e: any) {
      console.error('高德地图加载失败', e)
      mapError.value = `地图加载失败：${e?.message || e}（请检查 Key 是否为「Web端(JS API)」类型、安全密钥是否匹配）`
      return false
    }
  }

  function firstCoord(): [number, number] | null {
    for (const day of options.days.value) {
      for (const item of day.items) {
        if (hasCoords(item)) return [item.lng as number, item.lat as number]
      }
    }
    return null
  }

  async function retryMap() {
    mapInstance.value?.destroy?.()
    mapInstance.value = null
    amapPromise = null
    const ok = await ensureMap()
    if (ok) {
      redrawOverlays()
      fitAll()
    }
  }

  /** 切换地图上显示的天（0 = 全部） */
  function setMapDay(index: number) {
    mapDay.value = index
    redrawOverlays()
    nextTick(() => fitAll(false))
  }

  function redrawOverlays() {
    const map = mapInstance.value
    if (!map || !AMapLib) return

    if (dayMarkers.length || dayPolylines.length) {
      map.remove([...dayMarkers, ...dayPolylines])
    }
    dayMarkers = []
    dayPolylines = []
    markerEls.clear()

    const visibleDays =
      mapDay.value === 0
        ? options.days.value
        : options.days.value.filter((d) => d.day_index === mapDay.value)

    visibleDays.forEach((day) => {
      const color = dayColor(day.day_index - 1)
      const items = day.items

      // 1. 先画路线（放在标记下面）
      items.forEach((item, index) => {
        if (index >= items.length - 1) return
        const from = item
        const to = items[index + 1]
        if (!hasCoords(from) || !hasCoords(to)) return

        const seg = options.segmentOf(day.day_index, index)
        const hasPath = !!seg?.points?.length
        const path = hasPath
          ? seg!.points.map((p) => [p[0], p[1]])
          : [
              [from.lng as number, from.lat as number],
              [to.lng as number, to.lat as number]
            ]

        const highlighted = options.activeItem.value?.id === from.id

        // 白色描边，让路线在地图底色上更清晰
        dayPolylines.push(
          new AMapLib.Polyline({
            path,
            strokeColor: '#ffffff',
            strokeWeight: 9,
            strokeOpacity: 0.9,
            lineJoin: 'round',
            lineCap: 'round',
            zIndex: 50
          })
        )

        dayPolylines.push(
          new AMapLib.Polyline({
            path,
            strokeColor: hasPath ? color : '#94a3b8',
            strokeWeight: highlighted ? 7 : 5,
            strokeOpacity: 0.95,
            strokeStyle: hasPath ? 'solid' : 'dashed',
            showDir: hasPath,
            lineJoin: 'round',
            lineCap: 'round',
            zIndex: 51
          })
        )
      })

      // 2. 再画标记
      items.forEach((item, index) => {
        if (!hasCoords(item)) return

        const content = document.createElement('div')
        content.className = 'tp-marker'
        content.style.setProperty('--c', color)
        content.innerHTML =
          `<span class="tp-marker__pin">${index + 1}</span>` +
          `<span class="tp-marker__label">${esc(item.place_name)}</span>`

        const marker = new AMapLib.Marker({
          position: [item.lng, item.lat],
          content,
          anchor: 'center',
          zIndex: 100 + index,
          extData: { itemId: item.id }
        })

        marker.on('click', () => options.onSelectItem(item, day))
        dayMarkers.push(marker)

        markerEls.set(item.id, content)
        if (options.activeItem.value?.id === item.id) content.classList.add('is-active')
      })
    })

    if (dayMarkers.length || dayPolylines.length) {
      map.add([...dayPolylines, ...dayMarkers])
    }
    highlightMarker(options.activeItem.value?.id)
  }

  function highlightMarker(itemId?: number) {
    markerEls.forEach((el, id) => {
      el.classList.toggle('is-active', id === itemId)
    })
    syncLabelVisibility()
  }

  /** 地图缩得很小时隐藏地名标签，避免几十个标注糊成一团；悬停仍可看到 */
  function syncLabelVisibility() {
    const zoom = mapInstance.value?.getZoom?.() ?? 12
    const showAll = zoom >= 13.5
    markerEls.forEach((el, id) => {
      el.classList.toggle('label-hidden', !showAll && id !== options.activeItem.value?.id)
    })
  }

  function fitAll(animate = true) {
    const map = mapInstance.value
    if (!map) return
    const overlays = [...dayMarkers, ...dayPolylines]
    if (overlays.length) {
      map.setFitView(overlays, !animate, [80, 80, 80, 80], 15)
    }
  }

  /** 把地图视野移到某个地点 */
  function locateItem(item: TripItem, zoom = 14, duration = 350) {
    const map = mapInstance.value
    if (!map || !hasCoords(item)) return
    map.setZoomAndCenter(Math.max(map.getZoom(), zoom), [item.lng, item.lat], false, duration)
  }

  function openInfo(item: TripItem, day: TripDay) {
    if (!mapInstance.value || !infoWindow || !hasCoords(item)) return
    const color = dayColor(day.day_index - 1)
    const price =
      Number(item.cost_estimate) > 0
        ? `<div class="tp-info__row">门票预估 ¥${fmtMoney(item.cost_estimate)}</div>`
        : ''
    infoWindow.setContent(
      `<div class="tp-info">` +
        `<div class="tp-info__head"><span class="tp-info__dot" style="background:${color}"></span>${esc(item.place_name)}</div>` +
        `<div class="tp-info__row">🕘 ${esc(item.start_time)} – ${esc(item.end_time)}</div>` +
        price +
        `<div class="tp-info__foot">第 ${day.day_index} 天 · ${fmtDate(day.date)}</div>` +
        `</div>`
    )
    infoWindow.open(mapInstance.value, [item.lng, item.lat])
  }

  function closeInfo() {
    infoWindow?.close()
  }

  // ---------- 周边推荐的地图预览 ----------
  function clearPoiPreview() {
    if (nearbyMarkers.length) {
      mapInstance.value?.remove(nearbyMarkers)
      nearbyMarkers = []
    }
    previewInfo?.close()
  }

  /** 地图上展示一个 POI 预览点，地图还没准备好时返回 false */
  function showPoiPreview(poi: NearbyPoi): boolean {
    const map = mapInstance.value
    if (!map || !AMapLib) return false

    clearPoiPreview()

    const content = document.createElement('div')
    content.className = 'tp-marker tp-marker--poi'
    content.innerHTML = `<span class="tp-marker__pin">★</span>`

    const marker = new AMapLib.Marker({
      position: [poi.lng, poi.lat],
      content,
      anchor: 'center',
      zIndex: 300
    })
    nearbyMarkers.push(marker)
    map.add(marker)

    map.setZoomAndCenter(Math.max(map.getZoom(), 15), [poi.lng, poi.lat], false, 300)

    previewInfo?.setContent(
      `<div class="tp-info tp-info--poi">` +
        `<div class="tp-info__head">${esc(poi.name)}</div>` +
        `<div class="tp-info__row">${poi.rating ? `★ ${esc(poi.rating)} · ` : ''}距此 ${fmtDist(poi.distance)}</div>` +
        (poi.address ? `<div class="tp-info__row tp-info__row--muted">${esc(poi.address)}</div>` : '') +
        `</div>`
    )
    previewInfo?.open(map, [poi.lng, poi.lat])
    return true
  }

  /** 重置地图上仍选中的那天（比如切换地点时） */
  function resetMapDay() {
    mapDay.value = 0
    redrawOverlays()
  }

  function destroy() {
    clearPoiPreview()
    if (mapInstance.value) {
      mapInstance.value.destroy()
      mapInstance.value = null
    }
    dayMarkers = []
    dayPolylines = []
    markerEls.clear()
  }

  return {
    mapInstance,
    mapError,
    mapDay,
    ensureMap,
    retryMap,
    setMapDay,
    resetMapDay,
    redrawOverlays,
    highlightMarker,
    fitAll,
    locateItem,
    openInfo,
    closeInfo,
    showPoiPreview,
    clearPoiPreview,
    destroy
  }
}
