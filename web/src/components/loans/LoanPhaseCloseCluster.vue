<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import UiIcon from '../UiIcon.vue'
import LoanHoverHint from './LoanHoverHint.vue'
import type { LoanPhaseRareActionId, LoanPhaseRareMenuItem } from '../../utils/loanPhaseRareActions'

const props = defineProps<{
  phaseCloseLabelKey: string | null
  closeButtonClass: string
  phaseCloseDisabled: boolean
  closeHoverReason: string
  completePending: boolean
  rareMenuItems: LoanPhaseRareMenuItem[]
  shortcutPending: boolean
}>()

const emit = defineEmits<{
  completePhase: []
  rareAction: [id: LoanPhaseRareActionId, payload?: { reason: string }]
}>()

const { t } = useI18n()

const showCluster = computed(
  () => props.phaseCloseLabelKey != null || props.rareMenuItems.length > 0,
)

const hasChevron = computed(() => props.rareMenuItems.length > 0)

const menuOpen = ref(false)
const chevronRef = ref<HTMLButtonElement | null>(null)
const menuRef = ref<HTMLElement | null>(null)
const menuPosition = ref({ top: 0, left: 0 })

const reasonDraft = ref('')
const reasonMissing = ref(false)
const reasonActionId = ref<LoanPhaseRareActionId | null>(null)

const MENU_WIDTH = 280
const MENU_ITEM_HEIGHT = 36
const MENU_PADDING = 8
const REASON_PANEL_HEIGHT = 120

const menuHeight = computed(() => {
  let h = props.rareMenuItems.length * MENU_ITEM_HEIGHT + MENU_PADDING
  if (reasonActionId.value) h = REASON_PANEL_HEIGHT
  return h
})

function updateMenuPosition() {
  const el = chevronRef.value ?? menuRef.value
  if (!el && !chevronRef.value) return
  const anchor = chevronRef.value
  if (!anchor) return
  const rect = anchor.getBoundingClientRect()
  const gap = 4
  const h = menuHeight.value
  const fitsBelow = rect.bottom + gap + h <= window.innerHeight
  const top = fitsBelow ? rect.bottom + gap : rect.top - gap - h
  const left = Math.min(
    Math.max(8, rect.right - MENU_WIDTH),
    window.innerWidth - MENU_WIDTH - 8,
  )
  menuPosition.value = { top, left }
}

function closeMenu() {
  menuOpen.value = false
  reasonActionId.value = null
  reasonDraft.value = ''
  reasonMissing.value = false
}

function toggleMenu(event: MouseEvent) {
  event.stopPropagation()
  if (menuOpen.value) {
    closeMenu()
    return
  }
  reasonActionId.value = null
  reasonDraft.value = ''
  updateMenuPosition()
  menuOpen.value = true
}

function onDocumentPointerDown(event: PointerEvent) {
  if (!menuOpen.value) return
  const target = event.target as Node
  if (chevronRef.value?.contains(target) || menuRef.value?.contains(target)) return
  closeMenu()
}

let listenersAttached = false

function attachListeners() {
  if (listenersAttached) return
  document.addEventListener('pointerdown', onDocumentPointerDown)
  window.addEventListener('scroll', updateMenuPosition, true)
  window.addEventListener('resize', updateMenuPosition)
  listenersAttached = true
}

function detachListeners() {
  if (!listenersAttached) return
  document.removeEventListener('pointerdown', onDocumentPointerDown)
  window.removeEventListener('scroll', updateMenuPosition, true)
  window.removeEventListener('resize', updateMenuPosition)
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

watch(reasonActionId, () => {
  if (menuOpen.value) updateMenuPosition()
})

onUnmounted(() => {
  detachListeners()
})

function onMenuItemClick(item: LoanPhaseRareMenuItem) {
  if (props.shortcutPending) return
  if (item.needsReason) {
    reasonActionId.value = item.id
    reasonDraft.value = ''
    reasonMissing.value = false
    updateMenuPosition()
    return
  }
  if (!window.confirm(t(item.confirmKey))) return
  closeMenu()
  emit('rareAction', item.id)
}

function submitReason() {
  const id = reasonActionId.value
  if (!id) return
  if (!reasonDraft.value.trim()) {
    reasonMissing.value = true
    return
  }
  const item = props.rareMenuItems.find((row) => row.id === id)
  if (!item) return
  if (!window.confirm(t(item.confirmKey))) return
  const reason = reasonDraft.value.trim()
  closeMenu()
  emit('rareAction', id, { reason })
}

function chevronButtonClass(): string {
  const base = props.closeButtonClass
  if (props.phaseCloseLabelKey) {
    return `${base} rounded-l-none border-l border-primary-content/20 px-1.5 min-h-8 h-8`
  }
  return `${base} px-1.5 min-h-8 h-8`
}

function primaryButtonClass(): string {
  const base = props.closeButtonClass
  if (!hasChevron.value) return base
  return `${base} rounded-r-none border-r border-primary-content/20`
}
</script>

<template>
  <div v-if="showCluster" class="inline-flex shrink-0 items-stretch">
    <LoanHoverHint
      v-if="phaseCloseLabelKey"
      :text="closeHoverReason"
      :show-hint="Boolean(phaseCloseDisabled && closeHoverReason)"
      placement="below"
      :class="phaseCloseDisabled && closeHoverReason ? 'cursor-not-allowed' : ''"
    >
      <button
        type="button"
        :class="primaryButtonClass()"
        :disabled="phaseCloseDisabled"
        :aria-disabled="phaseCloseDisabled"
        @click="emit('completePhase')"
      >
        {{ t(phaseCloseLabelKey) }}
      </button>
    </LoanHoverHint>

    <div v-if="hasChevron" class="relative inline-flex">
      <button
        ref="chevronRef"
        type="button"
        :class="chevronButtonClass()"
        :disabled="shortcutPending"
        :aria-expanded="menuOpen"
        :aria-haspopup="true"
        :aria-label="t('loans.phaseRareActionsMenu')"
        @click="toggleMenu"
      >
        <UiIcon name="chevronDown" size-class="size-3.5" />
      </button>
      <Teleport to="body">
        <div
          v-if="menuOpen"
          ref="menuRef"
          class="fixed z-[200] w-[280px] rounded-box border border-base-200 bg-base-100 p-1 shadow-lg"
          :style="{
            top: `${menuPosition.top}px`,
            left: `${menuPosition.left}px`,
          }"
        >
          <template v-if="!reasonActionId">
            <ul class="menu menu-sm p-0" role="menu">
              <li v-for="item in rareMenuItems" :key="item.id" role="none">
                <button
                  type="button"
                  role="menuitem"
                  class="w-full justify-start"
                  :disabled="shortcutPending"
                  @click="onMenuItemClick(item)"
                >
                  {{ t(item.labelKey) }}
                </button>
              </li>
            </ul>
          </template>
          <div v-else class="space-y-2 p-2">
            <p class="text-xs font-medium">{{ t('loans.shortcutNotPickedUpAllReasonHint') }}</p>
            <input
              v-model="reasonDraft"
              type="text"
              class="input input-bordered input-sm w-full"
              :class="{ 'input-error': reasonMissing }"
              :placeholder="t('loans.reasonRequiredPlaceholder')"
              @keydown.enter.prevent="submitReason"
            />
            <div class="flex justify-end gap-2">
              <button type="button" class="btn btn-ghost btn-xs" @click="reasonActionId = null">
                {{ t('destructive.cancel') }}
              </button>
              <button
                type="button"
                class="btn btn-primary btn-xs"
                :disabled="shortcutPending"
                @click="submitReason"
              >
                {{ t('loans.shortcutExecute') }}
              </button>
            </div>
          </div>
        </div>
      </Teleport>
    </div>
  </div>
</template>
