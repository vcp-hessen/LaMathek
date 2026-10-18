<script setup lang="ts">
import { computed, nextTick, onUpdated, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type {
  BorrowerCalendarScope,
  CalendarScopeSwitchValue,
  InventoryCalendarScope,
} from '../../utils/calendarContent'
import {
  cycleBorrowerScope,
  cycleInventoryScope,
} from '../../utils/calendarContent'

const props = withDefaults(
  defineProps<{
    modelValue: CalendarScopeSwitchValue
    canManage?: boolean
    borrowerOnly?: boolean
    /** When true, only shows state; parent handles clicks (e.g. whole row). */
    passive?: boolean
  }>(),
  { canManage: false, borrowerOnly: false, passive: false },
)

const emit = defineEmits<{
  'update:modelValue': [value: CalendarScopeSwitchValue]
}>()

const { t } = useI18n()

const inputRef = ref<HTMLInputElement | null>(null)

const checked = computed(() => {
  if (props.borrowerOnly) {
    return props.modelValue === 'borrower'
  }
  return props.modelValue === 'all'
})

const indeterminate = computed(() => {
  if (props.borrowerOnly) return false
  return props.modelValue === 'contact'
})

/** DaisyUI tri-state checkbox uses aria-checked=mixed alongside :indeterminate. */
const ariaChecked = computed((): 'true' | 'false' | 'mixed' => {
  if (props.borrowerOnly) {
    return props.modelValue === 'borrower' ? 'true' : 'false'
  }
  switch (props.modelValue) {
    case 'all':
      return 'true'
    case 'contact':
      return 'mixed'
    default:
      return 'false'
  }
})

const title = computed(() => {
  if (props.borrowerOnly) {
    return props.modelValue === 'borrower'
      ? t('calendar.contentBorrower')
      : t('calendar.contentOff')
  }
  switch (props.modelValue) {
    case 'contact':
      return t('calendar.contentContact')
    case 'all':
      return t('calendar.contentAllLoans')
    default:
      return t('calendar.contentOff')
  }
})

function syncIndeterminate() {
  const el = inputRef.value
  if (!el) return
  el.indeterminate = indeterminate.value
}

watch(
  () => [props.modelValue, props.borrowerOnly] as const,
  () => void nextTick(syncIndeterminate),
  { immediate: true, flush: 'post' },
)

onUpdated(syncIndeterminate)

function onPassivePointerDown(event: MouseEvent) {
  if (!props.passive) return
  event.preventDefault()
  event.stopPropagation()
}

function onClick(event: MouseEvent) {
  if (props.passive) return
  event.preventDefault()
  if (props.borrowerOnly) {
    emit(
      'update:modelValue',
      cycleBorrowerScope(props.modelValue as BorrowerCalendarScope),
    )
    return
  }
  emit(
    'update:modelValue',
    cycleInventoryScope(props.modelValue as InventoryCalendarScope, props.canManage),
  )
}
</script>

<template>
  <input
    ref="inputRef"
    type="checkbox"
    class="checkbox checkbox-sm shrink-0"
    :class="{ 'pointer-events-none': passive }"
    :checked="checked"
    :aria-checked="ariaChecked"
    :tabindex="passive ? -1 : 0"
    :aria-label="title"
    :title="title"
    @click="onClick"
    @mousedown="onPassivePointerDown"
  />
</template>
