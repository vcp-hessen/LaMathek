<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { WLZ_GLYPH, type WlzGlyphId } from './wlz-glyphs'

const props = withDefaults(
  defineProps<{
    glyph: WlzGlyphId
    active?: boolean
    sizeClass?: string
    /** Menu label for tooltips; omit for WLZ lexicon, empty string for no tooltip */
    tooltip?: string
  }>(),
  {
    active: false,
    sizeClass: 'text-base',
  },
)

const { t } = useI18n()

const character = computed(() => WLZ_GLYPH[props.glyph])
const meaning = computed(() => t(`wlz.${props.glyph}`))

const titleAttr = computed(() => {
  if (props.tooltip !== undefined) {
    return props.tooltip.length > 0 ? props.tooltip : undefined
  }
  return meaning.value
})
</script>

<template>
  <span
    class="wlz-icon inline-flex shrink-0 items-center justify-center leading-none"
    :class="[sizeClass, active ? 'text-vcp-feuergelb' : '']"
    :title="titleAttr"
    aria-hidden="true"
  >
    {{ character }}
  </span>
</template>
