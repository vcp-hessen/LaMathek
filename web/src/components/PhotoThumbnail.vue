<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { photoUrl, type PhotoSize } from '../api/photos'

const PREVIEW_MAX_PX = 280
const SHOW_DELAY_MS = 180

const props = withDefaults(
  defineProps<{
    photoId: number | null | undefined
    size?: PhotoSize
    alt?: string
    class?: string
    /** Larger image on hover (table/list thumbnails). */
    preview?: boolean
  }>(),
  {
    size: '160',
    alt: '',
    class: 'size-10 shrink-0 overflow-hidden rounded bg-base-200',
    preview: true,
  },
)

const rootRef = ref<HTMLElement | null>(null)
const showPreview = ref(false)
const previewPos = ref({ top: 0, left: 0 })
let showTimer: ReturnType<typeof setTimeout> | undefined

const previewSize = computed((): PhotoSize | null => {
  if (!props.preview || props.size === 'full') return null
  if (props.size === '640') return 'full'
  return '640'
})

const previewSrc = computed(() =>
  props.photoId && previewSize.value ? photoUrl(props.photoId, previewSize.value) : '',
)

function placePreview() {
  const el = rootRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const gap = 10
  let left = rect.right + gap
  let top = rect.top + rect.height / 2 - PREVIEW_MAX_PX / 2
  top = Math.max(8, Math.min(top, window.innerHeight - PREVIEW_MAX_PX - 8))
  if (left + PREVIEW_MAX_PX > window.innerWidth - 8) {
    left = rect.left - PREVIEW_MAX_PX - gap
  }
  left = Math.max(8, left)
  previewPos.value = { top, left }
}

function onPointerEnter() {
  if (!previewSize.value || !props.photoId) return
  clearTimeout(showTimer)
  showTimer = setTimeout(() => {
    placePreview()
    showPreview.value = true
  }, SHOW_DELAY_MS)
}

function onPointerLeave() {
  clearTimeout(showTimer)
  showPreview.value = false
}

onBeforeUnmount(() => {
  clearTimeout(showTimer)
})
</script>

<template>
  <div
    v-if="photoId"
    ref="rootRef"
    :class="props.class"
    @pointerenter="onPointerEnter"
    @pointerleave="onPointerLeave"
  >
    <img
      :src="photoUrl(photoId, size)"
      :alt="alt"
      class="size-full max-w-none object-cover"
      loading="lazy"
    />
  </div>
  <Teleport v-if="previewSrc && showPreview" to="body">
    <div
      class="pointer-events-none fixed z-[200] overflow-hidden rounded-lg border border-base-300 bg-base-100 shadow-lg"
      :style="{
        top: `${previewPos.top}px`,
        left: `${previewPos.left}px`,
        width: `${PREVIEW_MAX_PX}px`,
        maxHeight: `${PREVIEW_MAX_PX}px`,
      }"
      role="presentation"
    >
      <img
        :src="previewSrc"
        alt=""
        class="size-full object-contain"
        width="280"
        height="280"
      />
    </div>
  </Teleport>
</template>
