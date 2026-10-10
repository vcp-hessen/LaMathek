<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import type { Inventory } from '../schemas/inventory'
import type { WlzGlyphId } from './wlz-glyphs'
import AppInventorySwitcher from './AppInventorySwitcher.vue'
import WlzIcon from './WlzIcon.vue'

const props = defineProps<{
  expanded: boolean
  activeInventoryId: number | null
  showInventoryPicker: boolean
  inventories: Inventory[]
  inventoriesLoading?: boolean
}>()

const route = useRoute()
const { t } = useI18n()

const workspaceLinks = computed(() => {
  const id = props.activeInventoryId
  if (id === null) return []
  const base = `/inventories/${id}`
  return [
    {
      key: 'material-types',
      to: `${base}/material-types`,
      routeName: 'inventory-material-types',
      label: t('nav.materialTypes'),
      glyph: 'split' as WlzGlyphId,
    },
    {
      key: 'pieces',
      to: `${base}/pieces`,
      routeName: 'inventory-pieces',
      label: t('nav.pieces'),
      glyph: 'full' as WlzGlyphId,
    },
    {
      key: 'stock',
      to: `${base}/stock`,
      routeName: 'inventory-stock',
      label: t('nav.stock'),
      glyph: 'empty' as WlzGlyphId,
    },
    {
      key: 'sets',
      to: `${base}/sets`,
      routeName: 'inventory-sets',
      label: t('nav.sets'),
      glyph: 'gather' as WlzGlyphId,
    },
    {
      key: 'loans',
      to: `${base}/loans`,
      routeName: 'inventory-loans',
      label: t('nav.loans'),
      glyph: 'exchange' as WlzGlyphId,
    },
  ]
})

function isWorkspaceLinkActive(linkRouteName: string): boolean {
  if (route.name === linkRouteName) return true
  if (linkRouteName === 'inventory-sets' && route.name === 'set-detail') return true
  if (linkRouteName === 'inventory-loans' && route.name === 'loan-detail') return true
  return false
}

function itemClass(active: boolean, expanded: boolean) {
  return [
    'flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm no-underline transition-colors',
    expanded ? '' : 'justify-center',
    active
      ? 'bg-white/15 font-medium text-white'
      : 'text-white/85 hover:bg-white/10',
  ]
}
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col gap-2">
    <div v-if="showInventoryPicker" class="shrink-0">
      <p
        v-show="expanded"
        class="mb-1 px-2 text-xs font-medium uppercase tracking-wide text-white/50"
      >
        {{ t('inventories.detail') }}
      </p>
      <div
        class="tooltip tooltip-right w-full"
        :class="{ 'before:hidden': expanded }"
        :data-tip="expanded ? undefined : t('inventories.activeLabel')"
      >
        <AppInventorySwitcher
          sidebar
          :expanded="expanded"
          :inventories="inventories"
          :loading="inventoriesLoading"
        />
      </div>
      <div
        v-if="activeInventoryId"
        class="my-2 border-t border-white/15"
        aria-hidden="true"
      />
    </div>

    <ul
      v-if="showInventoryPicker && activeInventoryId"
      class="min-h-0 flex-1 space-y-1 overflow-y-auto"
    >
      <li v-for="link in workspaceLinks" :key="link.key">
        <div
          class="tooltip tooltip-right w-full"
          :class="{ 'before:hidden': expanded }"
          :data-tip="expanded ? undefined : link.label"
        >
          <RouterLink
            :to="link.to"
            :class="itemClass(isWorkspaceLinkActive(link.routeName), expanded)"
            :aria-label="expanded ? undefined : link.label"
            :aria-current="isWorkspaceLinkActive(link.routeName) ? 'page' : undefined"
          >
            <WlzIcon
              :glyph="link.glyph"
              :active="isWorkspaceLinkActive(link.routeName)"
              size-class="text-lg"
              :tooltip="link.label"
            />
            <span v-show="expanded" class="truncate">{{ link.label }}</span>
          </RouterLink>
        </div>
      </li>
    </ul>
  </div>
</template>
