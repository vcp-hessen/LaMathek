<script setup lang="ts">
import type { Component } from 'vue'
import { Bars3Icon, ChevronDownIcon } from '@heroicons/vue/24/outline'

export type UiIconName = 'menu' | 'chevronDown'

const ICONS: Record<UiIconName, Component> = {
  menu: Bars3Icon,
  chevronDown: ChevronDownIcon,
}

withDefaults(
  defineProps<{
    name: UiIconName
    sizeClass?: string
  }>(),
  {
    sizeClass: 'size-5',
  },
)
</script>

<template>
  <component :is="ICONS[name]" :class="sizeClass" aria-hidden="true" />
</template>
