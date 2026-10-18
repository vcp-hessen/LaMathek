<script setup lang="ts">
import { nextTick, onUnmounted, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    text: string
    showHint?: boolean
    placement?: 'below' | 'above'
  }>(),
  { placement: 'below', showHint: true },
)

const anchorRef = ref<HTMLElement | null>(null)
const hintRef = ref<HTMLElement | null>(null)
const open = ref(false)
const position = ref({ top: 0, left: 0, maxWidth: 288 })

const GAP = 6
const MAX_WIDTH = 288

function updatePosition() {
  const anchor = anchorRef.value
  const hint = hintRef.value
  if (!anchor || !hint) return
  const rect = anchor.getBoundingClientRect()
  const hintHeight = hint.offsetHeight
  const maxWidth = Math.min(MAX_WIDTH, window.innerWidth - 16)
  const left = Math.min(
    Math.max(8, rect.right - maxWidth),
    window.innerWidth - maxWidth - 8,
  )
  let top =
    props.placement === 'above'
      ? rect.top - GAP - hintHeight
      : rect.bottom + GAP
  if (top < 8) {
    top = rect.bottom + GAP
  }
  if (top + hintHeight > window.innerHeight - 8) {
    top = Math.max(8, rect.top - GAP - hintHeight)
  }
  position.value = { top, left, maxWidth }
}

function onViewportChange() {
  if (open.value) updatePosition()
}

let listenersAttached = false

function attachListeners() {
  if (listenersAttached) return
  window.addEventListener('scroll', onViewportChange, true)
  window.addEventListener('resize', onViewportChange)
  listenersAttached = true
}

function detachListeners() {
  if (!listenersAttached) return
  window.removeEventListener('scroll', onViewportChange, true)
  window.removeEventListener('resize', onViewportChange)
  listenersAttached = false
}

function show() {
  if (!props.showHint || !props.text.trim()) return
  open.value = true
}

function hide() {
  open.value = false
}

watch(open, async (isOpen) => {
  if (isOpen) {
    attachListeners()
    await nextTick()
    updatePosition()
  } else {
    detachListeners()
  }
})

onUnmounted(() => {
  detachListeners()
})
</script>

<template>
  <span
    ref="anchorRef"
    class="relative inline-flex"
    @mouseenter="show"
    @mouseleave="hide"
    @focusin="show"
    @focusout="hide"
  >
    <slot />
    <Teleport to="body">
      <span
        v-if="open && showHint && text.trim()"
        ref="hintRef"
        role="tooltip"
        class="loan-hover-hint pointer-events-none fixed z-[200] rounded-md border border-base-300 bg-base-100 px-2.5 py-2 text-left text-xs font-normal leading-snug text-base-content shadow-md"
        :style="{
          top: `${position.top}px`,
          left: `${position.left}px`,
          maxWidth: `${position.maxWidth}px`,
        }"
      >
        {{ text }}
      </span>
    </Teleport>
  </span>
</template>
