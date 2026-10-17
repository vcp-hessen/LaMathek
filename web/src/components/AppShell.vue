<script setup lang="ts">
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { fetchInventories } from '../api/inventories'
import { fetchInstallationSettings } from '../api/settings'
import { stopImpersonation } from '../api/impersonation'
import { fetchMe, logout } from '../api/me'
import ActiveBoxPicker from './loans/ActiveBoxPicker.vue'
import AppBreadcrumbs from './AppBreadcrumbs.vue'
import { INVENTORY_WORKSPACE_ROUTE_NAMES } from '../utils/inventoryWorkspaceRoutes'
import AppFooter from './AppFooter.vue'
import AppSidebarChrome from './AppSidebarChrome.vue'
import UiIcon from './UiIcon.vue'
import { useInventoryStore } from '../stores/inventory'
import { useUiStore } from '../stores/ui'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const queryClient = useQueryClient()
const ui = useUiStore()
const inventoryStore = useInventoryStore()

const { data: settings } = useQuery({
  queryKey: ['settings'],
  queryFn: fetchInstallationSettings,
})

const { data: me } = useQuery({
  queryKey: ['me'],
  queryFn: fetchMe,
})

const { data: inventories, isLoading: inventoriesLoading } = useQuery({
  queryKey: ['inventories'],
  queryFn: fetchInventories,
  enabled: () => !!me.value,
})

const title = computed(() => settings.value?.title ?? t('app.productName'))
const inventoriesListActive = computed(
  () => route.path === '/inventories',
)
const settingsActive = computed(() => route.path === '/settings')
const diagnosticsActive = computed(() => route.path === '/diagnose')
const usersActive = computed(() => route.path === '/users')
const myLoansActive = computed(() => route.path === '/my-loans')

watch(
  () => route.fullPath,
  () => ui.closeMobileMenu(),
)

watch(
  () => [me.value, inventories.value] as const,
  ([user, list]) => {
    if (user && list) inventoryStore.reconcileWithAccessible(list)
  },
  { immediate: true },
)

const inventoryRouteNames = INVENTORY_WORKSPACE_ROUTE_NAMES

const headerInventoryId = computed(() => {
  if (!inventoryRouteNames.has(String(route.name))) return null
  const num = Number(route.params.id)
  return Number.isFinite(num) ? num : null
})

watch(
  () => [route.name, route.params.id] as const,
  ([name, rawId]) => {
    if (!name || !inventoryRouteNames.has(String(name))) return
    const num = Number(rawId)
    if (Number.isFinite(num)) inventoryStore.setActiveInventory(num)
  },
  { immediate: true },
)

async function onSignOut() {
  await logout()
  inventoryStore.setActiveInventory(null)
  await queryClient.cancelQueries()
  queryClient.clear()
  await router.push('/')
}

const impersonating = computed(() => !!me.value?.impersonation)

const sidebarShellClass = computed(() =>
  impersonating.value
    ? 'border-vcp-blau bg-vcp-feuergelb'
    : 'border-vcp-blau bg-vcp-blau',
)

async function onStopImpersonation() {
  await stopImpersonation()
  inventoryStore.setActiveInventory(null)
  await queryClient.invalidateQueries({ queryKey: ['me'] })
  await queryClient.invalidateQueries({ queryKey: ['inventories'] })
  await queryClient.invalidateQueries({ queryKey: ['users'] })
  await queryClient.invalidateQueries({ queryKey: ['audit-events'] })
}

async function onSidebarSignOut() {
  if (impersonating.value) {
    await onStopImpersonation()
  } else {
    await onSignOut()
  }
}
</script>

<template>
  <div class="flex min-h-dvh bg-base-200">
    <Teleport to="body">
      <div
        v-if="ui.mobileMenuOpen"
        class="fixed inset-0 z-40 flex md:hidden"
        role="dialog"
        :aria-label="t('shell.menu')"
      >
        <button
          type="button"
          class="absolute inset-0 bg-black/40"
          :aria-label="t('shell.closeMenu')"
          @click="ui.closeMobileMenu()"
        />
        <aside
          class="relative flex h-full w-64 max-w-[85vw] flex-col border-r shadow-xl"
          :class="sidebarShellClass"
        >
          <AppSidebarChrome
            :expanded="true"
            :title="title"
            :me="me"
            :impersonating="impersonating"
            :inventories="inventories ?? []"
            :inventories-loading="inventoriesLoading"
            :inventories-list-active="inventoriesListActive"
            :settings-active="settingsActive"
            :diagnostics-active="diagnosticsActive"
            :users-active="usersActive"
            :my-loans-active="myLoansActive"
            mobile
            @sign-out="onSidebarSignOut"
          />
        </aside>
      </div>
    </Teleport>

    <aside
      class="sticky top-0 z-10 hidden h-dvh shrink-0 flex-col border-r transition-[width] duration-200 md:flex"
      :class="[ui.sidebarExpanded ? 'w-56' : 'w-14', sidebarShellClass]"
    >
      <AppSidebarChrome
        :expanded="ui.sidebarExpanded"
        :title="title"
        :me="me"
        :impersonating="impersonating"
        :inventories="inventories ?? []"
        :inventories-loading="inventoriesLoading"
        :inventories-list-active="inventoriesListActive"
        :settings-active="settingsActive"
        :diagnostics-active="diagnosticsActive"
        :users-active="usersActive"
        :my-loans-active="myLoansActive"
        @sign-out="onSidebarSignOut"
      />
    </aside>

    <div class="flex min-h-0 min-w-0 flex-1 flex-col bg-base-100">
      <header class="navbar sticky top-0 z-20 border-b border-base-300/50 bg-base-100 shadow-sm">
        <div class="flex-none md:hidden">
          <button
            type="button"
            class="btn btn-square btn-ghost"
            :aria-label="t('shell.menu')"
            @click="ui.toggleMobileMenu()"
          >
            <UiIcon name="menu" />
          </button>
          <RouterLink to="/" class="btn btn-ghost btn-square" :aria-label="title">
            <img
              src="/logo.svg"
              width="32"
              height="32"
              alt=""
              class="size-8 rounded-lg"
            />
          </RouterLink>
        </div>
        <div class="flex min-w-0 flex-1 items-center gap-2 px-2 sm:gap-3">
          <AppBreadcrumbs class="min-w-0 flex-1" />
        </div>
        <ActiveBoxPicker
          v-if="me && headerInventoryId != null"
          :inventory-id="headerInventoryId"
          :show-when-logged-in="true"
          class="min-w-0 flex-none shrink pr-1 sm:shrink-0 sm:pr-2"
        />
        <div v-if="!me" class="flex-none pr-1 md:hidden">
          <a class="btn btn-primary btn-sm" href="/login">
            {{ t('auth.signIn') }}
          </a>
        </div>
      </header>

      <main class="flex min-h-0 flex-1 flex-col bg-base-100">
        <RouterView />
      </main>
      <AppFooter :settings="settings" />
    </div>
  </div>
</template>
