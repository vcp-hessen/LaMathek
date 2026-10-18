<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import type { Inventory } from '../schemas/inventory'
import type { WlzGlyphId } from './wlz-glyphs'
import AppCommandPalette from './AppCommandPalette.vue'
import AppInventorySwitcher from './AppInventorySwitcher.vue'
import WlzIcon from './WlzIcon.vue'

const props = defineProps<{
  expanded: boolean
  impersonating?: boolean
  activeInventoryId: number | null
  showInventoryPicker: boolean
  inventories: Inventory[]
  inventoriesLoading?: boolean
}>()

const route = useRoute()
const { t } = useI18n()
const paletteOpen = ref(false)

const canManageActive = computed(
  () => props.inventories.find((inv) => inv.id === props.activeInventoryId)?.canManage ?? false,
)

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
      key: 'material',
      to: `${base}/material`,
      routeName: 'inventory-material',
      label: t('nav.material'),
      glyph: 'please' as WlzGlyphId,
    },
    {
      key: 'sets',
      to: `${base}/sets`,
      routeName: 'inventory-sets',
      label: t('nav.sets'),
      glyph: 'gather' as WlzGlyphId,
    },
    {
      key: 'calendar',
      to: `${base}/calendar`,
      routeName: 'inventory-calendar',
      label: t('nav.calendar'),
      glyph: 'exchange' as WlzGlyphId,
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
  if (linkRouteName === 'inventory-material' && route.name === 'piece-detail') return true
  if (linkRouteName === 'inventory-material' && route.name === 'stock-lot-detail') return true
  return false
}

function itemClass(active: boolean, expanded: boolean) {
  if (props.impersonating) {
    return [
      'flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm no-underline transition-colors',
      expanded ? '' : 'justify-center',
      active
        ? 'bg-vcp-blau font-medium text-vcp-feuergelb'
        : 'text-vcp-blau/90 hover:bg-vcp-blau/10',
    ]
  }
  return [
    'flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm no-underline transition-colors',
    expanded ? '' : 'justify-center',
    active
      ? 'bg-white/15 font-medium text-white'
      : 'text-white/85 hover:bg-white/10',
  ]
}

const sectionLabelClass = computed(() =>
  props.impersonating
    ? 'mb-1 px-2 text-xs font-medium uppercase tracking-wide text-vcp-blau/50'
    : 'mb-1 px-2 text-xs font-medium uppercase tracking-wide text-white/50',
)

const dividerClass = computed(() =>
  props.impersonating ? 'border-vcp-blau/20' : 'border-white/15',
)
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col gap-2">
    <div v-if="showInventoryPicker" class="shrink-0">
      <p v-show="expanded" :class="sectionLabelClass">
        {{ t('inventories.detail') }}
      </p>
      <div v-if="activeInventoryId && canManageActive" class="mb-2">
        <button
          type="button"
          class="btn btn-ghost btn-sm w-full justify-start gap-2 border border-white/20"
          :class="[
            expanded ? '' : 'btn-square justify-center px-0',
            impersonating ? 'text-vcp-blau hover:bg-vcp-blau/10' : 'text-white/90 hover:bg-white/10',
          ]"
          :title="t('commandPalette.open')"
          @click="paletteOpen = true"
        >
          <span class="text-xs opacity-70">⌘K</span>
          <span v-show="expanded" class="truncate">{{ t('commandPalette.open') }}</span>
        </button>
      </div>
      <AppCommandPalette
        v-if="activeInventoryId"
        v-model:open="paletteOpen"
        :inventory-id="activeInventoryId"
        :can-manage="canManageActive"
      />
      <div
        class="tooltip tooltip-right w-full"
        :class="{ 'before:hidden': expanded }"
        :data-tip="expanded ? undefined : t('inventories.activeLabel')"
      >
        <AppInventorySwitcher
          sidebar
          :expanded="expanded"
          :impersonating="impersonating"
          :inventories="inventories"
          :loading="inventoriesLoading"
        />
      </div>
      <div
        v-if="activeInventoryId"
        class="my-2 border-t"
        :class="dividerClass"
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
