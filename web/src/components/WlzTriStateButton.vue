<script setup lang="ts">
import { computed } from 'vue'
import WlzIcon from './WlzIcon.vue'
import {
  cycleTriState,
  wlzGlyphForTriState,
  wlzTriStateButtonClass,
  type WlzTriState,
} from '../utils/wlzTriState'

const props = withDefaults(
  defineProps<{
    modelValue: WlzTriState
    size?: 'xs' | 'sm' | 'md'
    title?: string
    binary?: boolean
    allowPartial?: boolean
    /** When false, click is forwarded without cycling (e.g. Add-to-box). */
    cycleOnClick?: boolean
    disabled?: boolean
  }>(),
  {
    size: 'xs',
    binary: false,
    allowPartial: true,
    cycleOnClick: true,
    disabled: false,
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: WlzTriState]
  click: [event: MouseEvent]
}>()

const glyph = computed(() => wlzGlyphForTriState(props.modelValue))
const btnClass = computed(() => wlzTriStateButtonClass(props.modelValue, props.size))

function onClick(event: MouseEvent) {
  emit('click', event)
  if (!props.cycleOnClick || props.disabled) return
  emit(
    'update:modelValue',
    cycleTriState(props.modelValue, {
      binary: props.binary,
      allowPartial: props.allowPartial,
    }),
  )
}
</script>

<template>
  <button
    type="button"
    :class="btnClass"
    :disabled="disabled"
    :title="title"
    :aria-label="title"
    @click.stop="onClick"
  >
    <WlzIcon :glyph="glyph" size-class="text-sm" tooltip="" />
  </button>
</template>
