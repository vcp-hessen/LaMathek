<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { LoanLine } from '../../schemas/loan'
import UiIcon from '../UiIcon.vue'
import { lineRowActionSplit, type LineRowActionId } from './loanLineRowActions'

const props = defineProps<{
  line: LoanLine
  canManage: boolean
  isLoanBorrower: boolean
  canParticipate: boolean
  confirmAllowed: boolean
  confirmBlockedTitle?: string
  showReasonError?: boolean
}>()

const emit = defineEmits<{
  action: [payload: { id: LineRowActionId; lineId: number }]
}>()

const { t } = useI18n()

const options = computed(() => ({
  canManage: props.canManage,
  isLoanBorrower: props.isLoanBorrower,
  canParticipate: props.canParticipate,
  confirmAllowed: props.confirmAllowed,
}))

const split = computed(() => lineRowActionSplit(props.line, options.value))

const menuOpen = ref(false)
const chevronRef = ref<HTMLButtonElement | null>(null)
const menuRef = ref<HTMLElement | null>(null)
const menuPosition = ref({ top: 0, left: 0 })

const MENU_WIDTH = 192
const MENU_ITEM_HEIGHT = 36
const MENU_PADDING = 8

function itemTitle(item: { id: LineRowActionId; disabled?: boolean }): string | undefined {
  if (item.disabled && item.id === 'confirm' && props.confirmBlockedTitle) {
    return props.confirmBlockedTitle
  }
  return undefined
}

function updateMenuPosition() {
  const el = chevronRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const itemCount = split.value.alternatives.length
  const menuHeight = itemCount * MENU_ITEM_HEIGHT + MENU_PADDING
  const gap = 4
  const fitsBelow = rect.bottom + gap + menuHeight <= window.innerHeight
  const top = fitsBelow ? rect.bottom + gap : rect.top - gap - menuHeight
  const left = Math.min(
    Math.max(8, rect.right - MENU_WIDTH),
    window.innerWidth - MENU_WIDTH - 8,
  )
  menuPosition.value = { top, left }
}

function closeMenu() {
  menuOpen.value = false
}

function toggleMenu(event: MouseEvent) {
  event.stopPropagation()
  if (menuOpen.value) {
    closeMenu()
    return
  }
  updateMenuPosition()
  menuOpen.value = true
}

function onDocumentPointerDown(event: PointerEvent) {
  if (!menuOpen.value) return
  const target = event.target as Node
  if (chevronRef.value?.contains(target) || menuRef.value?.contains(target)) return
  closeMenu()
}

function onViewportChange() {
  if (menuOpen.value) updateMenuPosition()
}

let listenersAttached = false

function attachListeners() {
  if (listenersAttached) return
  document.addEventListener('pointerdown', onDocumentPointerDown)
  window.addEventListener('scroll', onViewportChange, true)
  window.addEventListener('resize', onViewportChange)
  listenersAttached = true
}

function detachListeners() {
  if (!listenersAttached) return
  document.removeEventListener('pointerdown', onDocumentPointerDown)
  window.removeEventListener('scroll', onViewportChange, true)
  window.removeEventListener('resize', onViewportChange)
  listenersAttached = false
}

watch(menuOpen, (open) => {
  if (open) {
    attachListeners()
    updateMenuPosition()
  } else {
    detachListeners()
  }
})

onUnmounted(() => {
  detachListeners()
})

function onSelect(id: LineRowActionId, disabled?: boolean) {
  if (disabled) return
  closeMenu()
  emit('action', { id, lineId: props.line.id })
}
</script>

<template>
  <div
    v-if="split.primary"
    class="relative flex justify-end"
    @click.stop
  >
    <div class="inline-flex items-stretch">
      <button
        type="button"
        class="btn btn-primary btn-xs h-7 min-h-7 max-w-[9rem] truncate rounded-r-none border-r border-primary-content/20 px-2"
        :class="{
          'btn-disabled': split.primary.disabled,
          'rounded-r-md': !split.alternatives.length,
        }"
        :disabled="split.primary.disabled"
        :title="itemTitle(split.primary)"
        @click="onSelect(split.primary.id, split.primary.disabled)"
      >
        {{ t(split.primary.labelKey) }}
      </button>
      <div v-if="split.alternatives.length">
        <button
          ref="chevronRef"
          type="button"
          class="btn btn-primary btn-xs h-7 min-h-7 rounded-l-none px-1.5"
          :aria-expanded="menuOpen"
          :aria-haspopup="true"
          :aria-label="t('loans.lineRowMoreActions')"
          @click="toggleMenu"
        >
          <UiIcon name="chevronDown" size-class="size-3.5" />
        </button>
        <Teleport to="body">
          <ul
            v-if="menuOpen"
            ref="menuRef"
            class="menu menu-sm fixed z-[200] w-48 rounded-box border border-base-200 bg-base-100 p-1 shadow-lg"
            role="menu"
            :style="{
              top: `${menuPosition.top}px`,
              left: `${menuPosition.left}px`,
            }"
          >
            <li v-for="item in split.alternatives" :key="item.id" role="none">
              <button
                type="button"
                role="menuitem"
                class="w-full justify-start"
                :class="{ 'opacity-50': item.disabled }"
                :disabled="item.disabled"
                :title="itemTitle(item)"
                @click="onSelect(item.id, item.disabled)"
              >
                {{ t(item.labelKey) }}
              </button>
            </li>
          </ul>
        </Teleport>
      </div>
    </div>
    <p
      v-if="showReasonError"
      role="alert"
      class="absolute right-0 top-full z-30 mt-1 w-52 rounded-md border border-error/40 bg-base-100 px-2 py-1.5 text-left text-xs leading-snug text-error shadow-md"
    >
      {{ t('loans.lineReasonMissingShort') }}
    </p>
  </div>
</template>
