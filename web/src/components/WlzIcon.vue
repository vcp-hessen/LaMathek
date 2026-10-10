<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { WLZ_GLYPH, type WlzGlyphId } from './wlz-glyphs'

const props = withDefaults(
  defineProps<{
    glyph: WlzGlyphId
    active?: boolean
    sizeClass?: string
  }>(),
  {
    active: false,
    sizeClass: 'text-base',
  },
)

const { t } = useI18n()

const character = computed(() => WLZ_GLYPH[props.glyph])
const meaning = computed(() => t(`wlz.${props.glyph}`))
</script>

<template>
  <span
    class="wlz-icon inline-flex shrink-0 items-center justify-center leading-none"
    :class="[sizeClass, active ? 'text-vcp-feuergelb' : '']"
    :title="meaning"
    aria-hidden="true"
  >
    {{ character }}
  </span>
</template>
