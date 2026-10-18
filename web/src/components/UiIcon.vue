<script setup lang="ts">
import type { Component } from 'vue'
import {
  ArchiveBoxIcon,
  ArchiveBoxXMarkIcon,
  ArrowPathIcon,
  ArrowUturnLeftIcon,
  Bars3Icon,
  CheckIcon,
  ChevronDownIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  HandRaisedIcon,
  NoSymbolIcon,
  PlusIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'

export type UiIconName =
  | 'menu'
  | 'chevronDown'
  | 'plus'
  | 'check'
  | 'x'
  | 'pack'
  | 'packOff'
  | 'pickup'
  | 'pickupOff'
  | 'return'
  | 'restock'
  | 'loss'
  | 'info'

const ICONS: Record<UiIconName, Component> = {
  menu: Bars3Icon,
  chevronDown: ChevronDownIcon,
  plus: PlusIcon,
  check: CheckIcon,
  x: XMarkIcon,
  pack: ArchiveBoxIcon,
  packOff: ArchiveBoxXMarkIcon,
  pickup: HandRaisedIcon,
  pickupOff: NoSymbolIcon,
  return: ArrowUturnLeftIcon,
  restock: ArrowPathIcon,
  loss: ExclamationTriangleIcon,
  info: InformationCircleIcon,
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
