<script setup lang="ts">
import {
  Map,
  Marker,
  NavigationControl,
  setWorkerUrl,
  type MapLayerMouseEvent,
} from 'maplibre-gl'
import { storeToRefs } from 'pinia'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useUiStore } from '../stores/ui'
import 'maplibre-gl/dist/maplibre-gl.css'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'

setWorkerUrl(workerUrl)

const OPENFREEMAP_LIGHT = 'https://tiles.openfreemap.org/styles/liberty'
const OPENFREEMAP_DARK = 'https://tiles.openfreemap.org/styles/dark'

const props = defineProps<{
  latitude: number | null
  longitude: number | null
  defaultLatitude: number
  defaultLongitude: number
}>()

const emit = defineEmits<{
  'update:latitude': [value: number | null]
  'update:longitude': [value: number | null]
}>()

const ui = useUiStore()
const { theme } = storeToRefs(ui)

const mapRoot = ref<HTMLElement | null>(null)
let map: Map | null = null
let marker: Marker | null = null
let resizeObserver: ResizeObserver | null = null

const styleUrl = computed(() =>
  theme.value === 'dark' ? OPENFREEMAP_DARK : OPENFREEMAP_LIGHT,
)

function hasMarker(): boolean {
  return props.latitude !== null && props.longitude !== null
}

function syncMarker(moveView = false) {
  if (!map) return
  if (hasMarker()) {
    const lngLat: [number, number] = [props.longitude!, props.latitude!]
    if (!marker) {
      marker = new Marker({ draggable: true, color: '#004287' })
        .setLngLat(lngLat)
        .addTo(map)
      marker.on('dragend', () => {
        const position = marker?.getLngLat()
        if (!position) return
        emit('update:latitude', position.lat)
        emit('update:longitude', position.lng)
      })
    } else {
      marker.setLngLat(lngLat)
    }
    if (moveView) {
      const zoom = Math.max(map.getZoom(), 13)
      map.easeTo({ center: lngLat, zoom, duration: 300 })
    }
  } else if (marker) {
    marker.remove()
    marker = null
    if (moveView) {
      map.easeTo({
        center: [props.defaultLongitude, props.defaultLatitude],
        zoom: 8,
        duration: 300,
      })
    }
  }
}

function initMap() {
  if (!mapRoot.value || map) return
  const center: [number, number] = hasMarker()
    ? [props.longitude!, props.latitude!]
    : [props.defaultLongitude, props.defaultLatitude]

  map = new Map({
    container: mapRoot.value,
    style: styleUrl.value,
    center,
    zoom: hasMarker() ? 13 : 8,
    scrollZoom: false,
    attributionControl: { compact: true },
  })

  map.addControl(new NavigationControl({ showCompass: false }), 'top-right')

  map.on('click', (event: MapLayerMouseEvent) => {
    emit('update:latitude', event.lngLat.lat)
    emit('update:longitude', event.lngLat.lng)
  })

  map.on('load', () => {
    syncMarker(false)
    map?.resize()
  })

  resizeObserver = new ResizeObserver(() => {
    map?.resize()
  })
  resizeObserver.observe(mapRoot.value)
}

onMounted(() => {
  initMap()
})

watch(styleUrl, (url) => {
  if (!map) return
  map.setStyle(url)
})

watch(
  () =>
    [props.latitude, props.longitude, props.defaultLatitude, props.defaultLongitude] as const,
  () => {
    syncMarker(true)
  },
)

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
  marker?.remove()
  marker = null
  map?.remove()
  map = null
})
</script>

<template>
  <div
    ref="mapRoot"
    class="h-56 w-full overflow-hidden rounded-lg border border-base-200"
    role="application"
    aria-label="Karte"
  />
</template>
