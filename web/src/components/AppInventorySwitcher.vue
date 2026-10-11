<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import type { Inventory } from '../schemas/inventory'
import { useInventoryStore } from '../stores/inventory'
import UiIcon from './UiIcon.vue'
import WlzIcon from './WlzIcon.vue'

const props = withDefaults(
  defineProps<{
    inventories: Inventory[]
    loading?: boolean
    sidebar?: boolean
    expanded?: boolean
  }>(),
  { sidebar: false, expanded: true },
)

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const inventoryStore = useInventoryStore()

const inventorySectionRoutes = new Set([
  'inventory-material-types',
  'inventory-material',
  'inventory-sets',
  'inventory-loans',
])

const inventoryDetailRoutes = new Set(['set-detail', 'loan-detail', 'piece-detail'])

const hasInventories = computed(() => props.inventories.length > 0)

const activeInventory = computed(() => {
  const id = inventoryStore.activeInventoryId
  if (id === null) return null
  return props.inventories.find((i) => i.id === id) ?? null
})

const selectValue = computed(() => {
  if (!hasInventories.value) return ''
  if (activeInventory.value) return String(activeInventory.value.id)
  return ''
})

const triggerLabel = computed(() => activeInventory.value?.name ?? t('inventories.pickActive'))

const menuOpen = ref(false)
const rootRef = ref<HTMLElement | null>(null)
const menuRef = ref<HTMLElement | null>(null)
const triggerRef = ref<HTMLButtonElement | null>(null)
const menuPosition = ref({ top: 0, left: 0, width: 208 })

function updateMenuPosition() {
  const el = triggerRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  if (props.expanded) {
    menuPosition.value = {
      top: rect.bottom + 4,
      left: rect.left,
      width: rect.width,
    }
    return
  }
  menuPosition.value = {
    top: rect.top,
    left: rect.right + 4,
    width: 208,
  }
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
  if (rootRef.value?.contains(target) || menuRef.value?.contains(target)) return
  closeMenu()
}

function onViewportChange() {
  if (menuOpen.value) updateMenuPosition()
}

onMounted(() => {
  document.addEventListener('pointerdown', onDocumentPointerDown)
  window.addEventListener('resize', onViewportChange)
  window.addEventListener('scroll', onViewportChange, true)
})

onUnmounted(() => {
  document.removeEventListener('pointerdown', onDocumentPointerDown)
  window.removeEventListener('resize', onViewportChange)
  window.removeEventListener('scroll', onViewportChange, true)
})

watch(
  () => props.expanded,
  () => {
    closeMenu()
  },
)

function navigateToInventory(id: number) {
  inventoryStore.setActiveInventory(id)
  const name = route.name ? String(route.name) : ''
  if (inventorySectionRoutes.has(name)) {
    void router.push({ name, params: { ...route.params, id: String(id) } })
    return
  }
  if (inventoryDetailRoutes.has(name)) {
    void router.push(`/inventories/${id}/material-types`)
    return
  }
  void router.push(`/inventories/${id}/material-types`)
}

function onChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  if (!value) return
  navigateToInventory(Number(value))
}

function pick(id: number) {
  navigateToInventory(id)
  closeMenu()
}
</script>

<template>
  <div ref="rootRef" :class="sidebar ? 'w-full min-w-0' : 'flex shrink-0 items-center gap-2'">
    <template v-if="loading">
      <span :class="sidebar ? 'text-xs text-white/60' : 'text-sm text-base-content/60'">
        {{ t('auth.loading') }}
      </span>
    </template>
    <template v-else-if="!hasInventories">
      <span
        class="badge badge-sm w-full max-w-none truncate font-normal"
        :class="
          sidebar
            ? 'justify-center border-white/30 bg-transparent text-xs text-white/70'
            : 'badge-outline max-w-[14rem] text-base-content/70'
        "
        role="status"
      >
        {{ t('inventories.noneAccessible') }}
      </span>
    </template>
    <template v-else-if="sidebar">
      <button
        ref="triggerRef"
        type="button"
        class="flex w-full min-w-0 items-center rounded-lg border border-white/30 bg-white/5 text-white hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
        :class="
          expanded
            ? 'h-8 gap-1 px-2 text-xs'
            : 'btn btn-ghost btn-sm btn-square min-h-8 justify-center border-0 bg-transparent hover:bg-white/10'
        "
        :aria-expanded="menuOpen"
        :aria-haspopup="true"
        :aria-label="expanded ? t('inventories.activeLabel') : undefined"
        @click="toggleMenu"
      >
        <WlzIcon
          v-if="!expanded"
          glyph="campPath"
          size-class="text-lg"
          :tooltip="t('inventories.activeLabel')"
        />
        <template v-else>
          <span class="min-w-0 flex-1 truncate text-left">{{ triggerLabel }}</span>
          <UiIcon name="chevronDown" size-class="size-3.5 shrink-0 opacity-70" />
        </template>
      </button>
      <Teleport to="body">
        <ul
          v-if="menuOpen"
          ref="menuRef"
          class="fixed z-[200] max-h-48 overflow-y-auto rounded-lg border border-white/25 bg-[#1a5593] p-1 shadow-lg"
          :style="{
            top: `${menuPosition.top}px`,
            left: `${menuPosition.left}px`,
            width: `${menuPosition.width}px`,
          }"
          role="listbox"
          :aria-label="t('inventories.activeLabel')"
        >
          <li v-for="inv in inventories" :key="inv.id" role="option" :aria-selected="inv.id === activeInventory?.id">
            <button
              type="button"
              class="w-full truncate rounded-md px-2 py-1.5 text-left text-xs text-white hover:bg-white/10"
              :class="inv.id === activeInventory?.id ? 'bg-white/15 font-medium' : ''"
              @click="pick(inv.id)"
            >
              {{ inv.name }}
            </button>
          </li>
        </ul>
      </Teleport>
    </template>
    <template v-else>
      <label class="sr-only" for="active-inventory">{{ t('inventories.activeLabel') }}</label>
      <select
        id="active-inventory"
        class="select select-sm select-bordered max-w-[10rem] sm:max-w-[14rem]"
        :value="selectValue"
        :aria-label="t('inventories.activeLabel')"
        @change="onChange"
      >
        <option v-if="selectValue === ''" disabled value="">
          {{ t('inventories.pickActive') }}
        </option>
        <option v-for="inv in inventories" :key="inv.id" :value="inv.id">
          {{ inv.name }}
        </option>
      </select>
    </template>
  </div>
</template>
